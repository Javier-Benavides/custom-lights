"""Sends colors to a slow device (a mouse, a GPU, a keyboard) from its own thread, without holding up the light loop.

The loop leaves the color and moves on: it never waits for the device. If several colors arrive before one is sent,
the last one wins; with `average`, their average in linear light. That way the GPU, which changes every few seconds,
follows the background color of the scene and not one flicker of the fire.

It sends only when the bytes change, plus a refresh in case the device restarted: these devices do not say what they
show. If a device fails or goes away, it is released and looked for again every `retry_s`.
"""
import math
import threading
import time

from .color import to_bytes

BLACK = (0, 0, 0)


class Emitter:
    def __init__(self, name, open_device, interval_s, refresh_s=60.0, retry_s=5.0, average=False, clock=time.monotonic):
        self.name, self._open, self._clock = name, open_device, clock
        self.interval_s, self.refresh_s, self.retry_s, self.average = interval_s, refresh_s, retry_s, average
        self._cond = threading.Condition()
        self._sum, self._n = (0.0, 0.0, 0.0), 0
        self._color = None
        self._device = None
        self._thread = None
        self._stop = False
        self._black_on_exit = True
        self._last_decision = self._last_send = self._next_try = -math.inf
        self.sent = None          # the last bytes the device accepted
        self.problem = None
        self.sends = 0

    def put(self, linear):
        """Called by the light loop. It never waits."""
        with self._cond:
            if self.average and self._n:
                self._sum = tuple(a + b for a, b in zip(self._sum, linear))
                self._n += 1
            else:
                self._sum, self._n = tuple(linear), 1
            self._cond.notify()

    def wait(self, now):
        """How long until the next step: 0 is now; None, until a color arrives."""
        if self._device is None and now < self._next_try:
            return self._next_try - now
        left = self.interval_s - (now - self._last_decision)
        if left > 0:
            return left
        if self._n or (self._color is not None and self.sent is None):
            return 0.0
        if self._color is None:
            return None
        return max(0.0, self.refresh_s - (now - self._last_send))

    def step(self, now):
        """Takes the pending color and sends it if it changed or a refresh is due."""
        with self._cond:
            if self._n:
                self._color = tuple(c / self._n for c in self._sum)
                self._sum, self._n = (0.0, 0.0, 0.0), 0
            color = self._color
        if color is None:
            return
        self._last_decision = now
        rgb = to_bytes(color)
        if rgb == self.sent and now - self._last_send < self.refresh_s:
            return
        self._send(rgb, now)

    def _send(self, rgb, now):
        try:
            if self._device is None:
                self._device = self._open()
            self._device.show(rgb)
        except (OSError, ValueError) as e:      # ValueError: the allow-list refused something. Reported, not retried often
            self.problem = f"{self.name}: {e}"
            self._release()
            self.sent = None
            self._next_try = now + self.retry_s
            return
        self.sent, self._last_send, self.problem = rgb, now, None
        self.sends += 1

    def _release(self):
        if self._device is not None:
            try:
                self._device.close()
            except OSError:
                pass
        self._device = None

    def _loop(self):
        while True:
            with self._cond:
                while not self._stop:
                    left = self.wait(self._clock())
                    if left is not None and left <= 0:
                        break
                    self._cond.wait(left)
                if self._stop:
                    break
            self.step(self._clock())
        if self._black_on_exit:
            try:
                if self._device is None:
                    self._device = self._open()
                self._device.show(BLACK)
                self.sent = BLACK
            except (OSError, ValueError):
                pass
        self._release()

    def start(self):
        self._thread = threading.Thread(target=self._loop, name=f"luces-{self.name}", daemon=True)
        self._thread.start()

    def stop(self, black=True, timeout_s=1.5):
        """Stops the thread. With `black`, it leaves the device black (the GPU, in its off mode)."""
        with self._cond:
            self._stop, self._black_on_exit = True, black
            self._cond.notify()
        if self._thread is not None:
            self._thread.join(timeout_s)

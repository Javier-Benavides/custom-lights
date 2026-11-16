"""The service: on each cycle it reads what was asked for, computes the scene and sends it to the LEDs.

No network, no ports and no disk writes. It only sends when the frame changes, plus a refresh every minute in case the
chip restarted.
"""
import math
import os
import signal
import sys
import time

from . import paths, scenes
from . import settings as st
from .color import hex_to_rgb, quantize, to_linear
from .hardware import ite

REFRESH_S = 60.0
RETRY_S = 10.0
TRANSITION_S = 8.0


def current_scene(control, now, initial):
    """(scene, color). A timed scene such as `breathe` goes back by itself to the one before."""
    scene = control.get("scene") if control.get("scene") in scenes.SCENES else initial
    until = control.get("until")
    if isinstance(until, (int, float)) and now >= until:
        back_to = control.get("back_to")
        scene = back_to if back_to in scenes.SCENES else initial
    color = control.get("color") if isinstance(control.get("color"), str) and st.HEX.fullmatch(control["color"]) else None
    return scene, color


def requested_brightness(control):
    b = control.get("brightness", 100)
    return max(0.0, min(100.0, b)) / 100 if isinstance(b, (int, float)) and not isinstance(b, bool) else 1.0


class Fade:
    """Smooths in linear light: takes each zone towards its target with no jumps."""

    def __init__(self):
        self.current = {zone: (0.0, 0.0, 0.0) for zone in scenes.ZONES}

    def step(self, target, dt, time_constant):
        alpha = 1 - math.exp(-dt / time_constant) if time_constant > 0 else 1.0
        for zone in self.current:
            self.current[zone] = tuple(a + (b - a) * alpha for a, b in zip(self.current[zone], target[zone]))
        return self.current


def linear_target(result, settings, brightness):
    """Brightness scales as the eye sees it. The limit is one of current: it applies to the light, at the end."""
    g = settings["general"]
    limit = g["max_brightness"] / 100
    return {z: tuple(c * limit for c in to_linear(rgb, value * brightness, g["gamma"])) for z, (rgb, value) in result.items()}


def with_flash(linear, flash, settings, brightness):
    """Lightning goes on top, after smoothing: it lasts less than the smoothing does."""
    if not flash:
        return linear
    lightning = settings["sky"]["lightning"]
    yellow = linear_target({"flash": (hex_to_rgb(lightning["color"]), lightning["brightness"] / 100)}, settings, brightness)["flash"]
    return {z: tuple(a + (b - a) * flash.get(z, 0.0) for a, b in zip(c, yellow)) for z, c in linear.items()}


def frame(linear, settings, on=1.0):
    return {z["header"]: quantize(linear[name], z["leds"], on) for name, z in settings["zones"].items()}


class Service:
    def __init__(self, open_output=ite.Controller, clock=time.time, sleep=time.sleep):
        self.open_output, self.clock, self.sleep = open_output, clock, sleep
        self.stop = False
        self.settings = st.load()
        self.settings_error = None
        self.place = None
        self.signatures = {}
        self.control = {}
        self.weather = self.solar = None
        self.fade = Fade()
        self.output = None
        self.output_leds = None
        self.scene = None
        self.started_at = 0.0
        self.last_frame = None
        self.last_sent = 0.0
        self.last_status = 0.0
        self.last_cycle = None
        self.problem = None

    def _changed(self, path):
        try:
            s = os.stat(path)
            signature = (s.st_mtime_ns, s.st_size)
        except OSError:
            signature = None
        if self.signatures.get(path, "nothing") == signature:
            return False
        self.signatures[path] = signature
        return True

    def reload(self):
        path = paths.control("settings.toml")
        if self._changed(path):
            try:
                self.settings = st.load(path)
                self.settings_error = None
            except (st.InvalidSettings, OSError) as e:
                self.settings_error = str(e)      # keeps going with the last valid settings
                print(f"settings: {e}", file=sys.stderr)
        path = paths.control("place.toml")
        if self._changed(path):
            try:
                self.place = st.load_place(path)
            except (st.InvalidSettings, OSError) as e:
                self.settings_error = str(e)
        path = paths.control("mode.json")
        if self._changed(path):
            self.control = st.read_json(path) or {}
        path = paths.data("weather.json")
        if self._changed(path):
            self.weather = st.read_json(path)
        path = paths.data("solar.json")
        if self._changed(path):
            self.solar = st.read_json(path)

    def _leds(self):
        return {z["header"]: z["leds"] for z in self.settings["zones"].values()}

    def _connect(self):
        if self.output is not None and self.output_leds == self._leds():
            return True
        self._release()
        try:
            self.output = self.open_output()
            self.output.start(self._leds())
            self.output_leds = self._leds()
            self.last_frame = None
            self.problem = None
            return True
        except OSError as e:
            self.problem = f"output: {e}"
            self._release()
            return False

    def _release(self):
        if self.output is not None:
            try:
                self.output.close()
            except OSError:
                pass
        self.output = None

    def cycle(self):
        """One step. Returns how long to sleep."""
        now = self.clock()
        self.reload()
        scene, color = current_scene(self.control, now, self.settings["general"]["initial_scene"])
        if scene != self.scene:
            self.scene, self.started_at = scene, now
        if not self._connect():
            self._publish(now)
            return RETRY_S
        forced = self.control.get("forced_until")
        forced = forced if isinstance(forced, (int, float)) and not isinstance(forced, bool) else None
        demo = self.control.get("demo") if isinstance(self.control.get("demo"), dict) else None
        ctx = scenes.Context(now, self.settings, self.place, self.weather, self.solar, self.started_at, color, forced, demo)
        brightness = requested_brightness(self.control)
        target = linear_target(scenes.render(scene, ctx), self.settings, brightness)
        transition = now - self.started_at < TRANSITION_S
        dt = 0.0 if self.last_cycle is None else min(now - self.last_cycle, 30.0)
        self.last_cycle = now
        linear = self.fade.step(target, dt, 1.5 if transition else scenes.SCENES[scene].smoothing_s)
        flash = scenes.flash(scene, ctx)
        on = 1.0 if flash else scenes.leds_on(scene, ctx)
        new = frame(with_flash(linear, flash, self.settings, brightness), self.settings, on)
        if new != self.last_frame or now - self.last_sent >= REFRESH_S:
            try:
                self.output.paint(new)
                self.last_frame, self.last_sent = new, now
            except OSError as e:
                self.problem = f"output: {e}"
                self._release()
                return RETRY_S
        self._publish(now)
        delay = scenes.frame_delay(scene, ctx)
        return min(0.25, delay) if transition else delay

    def _publish(self, now):
        if now - self.last_status < 30 and self.problem is None:
            return
        self.last_status = now
        try:
            st.write_json(paths.run("status.json"), {
                "time": now, "scene": self.scene, "settings_error": self.settings_error, "problem": self.problem,
                "firmware": self.output.info.get("firmware") if self.output else None})
        except OSError:
            pass

    def lights_out(self):
        if self.output is not None:
            try:
                self.output.paint({h: [(0, 0, 0)] * n for h, n in self._leds().items()})
            except OSError:
                pass
        self._release()

    def run(self):
        signal.signal(signal.SIGTERM, lambda *_: setattr(self, "stop", True))
        signal.signal(signal.SIGINT, lambda *_: setattr(self, "stop", True))
        while not self.stop:
            self.sleep(self.cycle())
        self.lights_out()


def main():
    Service().run()
    return 0

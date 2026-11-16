"""The service: on each cycle it reads what was asked for, computes the scene and sends it to the LEDs.

No network, no ports and no disk writes. It only sends when the frame changes, plus a refresh every minute in case the
chip restarted.

A mouse, a GPU light and a keyboard can follow the color of one zone. Each one runs in its own thread (`emitter.py`): the
loop leaves the color and moves on, because a GPU color takes about 140 ms and the `sun` scene runs at 15 frames a second.
"""
import math
import os
import signal
import sys
import time

from . import emitter, paths, scenes
from . import settings as st
from .color import hex_to_rgb, quantize, to_linear
from .hardware import ite, msi_gpu, razer, xpg_sorcerer

REFRESH_S = 60.0
RETRY_S = 10.0
TRANSITION_S = 8.0
MOUSE_INTERVAL_S = 0.05     # up to 20 colors a second: the sun scene runs at 15
DEVICES = {"mouse": razer.Mouse, "gpu": msi_gpu.Gpu, "keyboard": xpg_sorcerer.KeyboardLights}


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


def luminance(linear):
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def with_floor(color, floor):
    """A floor of light, so the keyboard is never dark. What the color lacks to reach the floor's luminance is filled
    with the floor's color: darker than the floor, it ends as bright as the floor and takes on its hue; brighter, it
    does not change. A color with the floor's hue stays right on the floor."""
    missing = 1 - luminance(color) / luminance(floor) if luminance(floor) > 0 else 0.0
    return tuple(c + f * missing for c, f in zip(color, floor)) if missing > 0 else color


def device_color(linear, on, device, gamma):
    """The color of its zone, with the share of LEDs still on (at nightfall they go out one by one) and its
    brightness, which is as the eye sees it: it goes through gamma, like the brightness of scenes. Above 100 the light
    rises without changing the hue: if a channel passes the maximum, all three come down together. With `floor`, it
    never goes below that floor, in the device's bytes."""
    factor = (device["brightness"] / 100) ** gamma * on
    color = tuple(c * factor for c in linear[device["zone"]])
    largest = max(color)
    color = tuple(c / largest for c in color) if largest > 1 else color
    return with_floor(color, hex_to_rgb(device["floor"])) if device.get("floor") else color


class Service:
    def __init__(self, open_output=ite.Controller, clock=time.time, sleep=time.sleep, devices=None):
        """`devices`: {"mouse": open, "gpu": open, "keyboard": open}. With none it drives no device, so tests never
        touch hardware. `main` passes the real ones."""
        self.open_output, self.clock, self.sleep = open_output, clock, sleep
        self.open_device = dict(devices or {})
        self.emitters = {}
        self.devices_signature = None
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

    def _emitters_up_to_date(self):
        """Starts, changes or stops the thread of each device to match the settings."""
        for name, open_device in self.open_device.items():
            device = self.settings[name]
            key = (device["enabled"], device.get("interval_s"), device.get("refresh_s"))
            current = self.emitters.get(name)
            if current is not None and current[0] == key:
                continue
            if current is not None:
                current[1].stop(black=not device["enabled"])
                del self.emitters[name]
            if device["enabled"]:
                e = emitter.Emitter(name, open_device, device.get("interval_s", MOUSE_INTERVAL_S),
                                    refresh_s=device.get("refresh_s", 60.0), average=name == "gpu")
                e.start()
                self.emitters[name] = (key, e)

    def _to_devices(self, linear, on):
        for name, (_, e) in self.emitters.items():
            e.put(device_color(linear, on, self.settings[name], self.settings["general"]["gamma"]))

    def cycle(self):
        """One step. Returns how long to sleep."""
        now = self.clock()
        self.reload()
        self._emitters_up_to_date()
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
        final = with_flash(linear, flash, self.settings, brightness)
        self._to_devices(final, on)
        new = frame(final, self.settings, on)
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
        signature = tuple((n, e.problem, e.sent is None) for n, (_, e) in sorted(self.emitters.items()))
        if now - self.last_status < 30 and self.problem is None and signature == self.devices_signature:
            return
        self.last_status, self.devices_signature = now, signature
        try:
            st.write_json(paths.run("status.json"), {
                "time": now, "scene": self.scene, "settings_error": self.settings_error, "problem": self.problem,
                "firmware": self.output.info.get("firmware") if self.output else None,
                "devices": {n: {"color": e.sent, "problem": e.problem, "sends": e.sends}
                            for n, (_, e) in self.emitters.items()}})
        except OSError:
            pass

    def lights_out(self):
        if self.output is not None:
            try:
                self.output.paint({h: [(0, 0, 0)] * n for h, n in self._leds().items()})
            except OSError:
                pass
        self._release()
        for _, e in self.emitters.values():
            e.stop(black=True)
        self.emitters = {}

    def run(self):
        signal.signal(signal.SIGTERM, lambda *_: setattr(self, "stop", True))
        signal.signal(signal.SIGINT, lambda *_: setattr(self, "stop", True))
        while not self.stop:
            self.sleep(self.cycle())
        self.lights_out()


def main():
    Service(devices=DEVICES).run()
    return 0

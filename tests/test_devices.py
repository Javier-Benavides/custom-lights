"""The mouse, the GPU light and the keyboard in the service, with fake devices: they follow a zone, the loop never waits
for them, and the keyboard is never dark."""
import calendar
import contextlib
import io
import os
import threading
import time
import unittest

from luces import cli, paths, service
from luces import settings as st
from luces.color import hex_to_rgb, to_bytes, to_linear
from tests.helpers import SETTINGS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEYBOARD = SETTINGS["keyboard"]
BLACK = {"case": (0.0, 0.0, 0.0), "cooler": (0.0, 0.0, 0.0), "rear": (0.0, 0.0, 0.0)}


def write(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def read(*path):
    with open(os.path.join(ROOT, *path), encoding="utf-8") as f:
        return f.read()


def keyboard_bytes(linear, on=1.0, device=KEYBOARD):
    return to_bytes(service.device_color(linear, on, device, SETTINGS["general"]["gamma"]))


class FakeDevice:
    def __init__(self, delay=0.0):
        self.colors, self.delay = [], delay
        self.lock = threading.Lock()

    def open(self):
        return self

    def show(self, rgb):
        if self.delay:
            time.sleep(self.delay)
        with self.lock:
            self.colors.append(rgb)

    def close(self):
        pass


class FakeChip:
    info = {"firmware": "1.2.3.4"}

    def start(self, leds):
        pass

    def paint(self, frame):
        pass

    def close(self):
        pass


class ServiceWithDevices(unittest.TestCase):
    def setUp(self):
        for folder in (paths.CONTROL, paths.DATA, paths.RUN):
            for f in os.listdir(folder):
                os.unlink(os.path.join(folder, f))
        write(paths.control("settings.toml"), "[mouse]\nenabled = true\n\n[gpu]\nenabled = true\n")
        self.t = calendar.timegm((2026, 11, 5, 18, 0, 0))
        self.mouse, self.gpu = FakeDevice(), FakeDevice(delay=0.14)    # one GPU color: about 140 ms

    def service(self):
        return service.Service(open_output=FakeChip, clock=lambda: self.t, sleep=lambda s: None,
                               devices={"mouse": self.mouse.open, "gpu": self.gpu.open})

    def mode(self, **m):
        st.write_json(paths.control("mode.json"), m)

    def test_the_loop_never_waits(self):
        s = self.service()
        self.mode(scene="sun", forced_until=self.t + 3600)
        worst = 0.0
        try:
            for _ in range(15):
                start = time.monotonic()
                s.cycle()
                worst = max(worst, time.monotonic() - start)
                self.t += 1 / 15
                time.sleep(1 / 15)
        finally:
            s.lights_out()
        self.assertLess(worst, 0.1, "a cycle waited for a device")
        self.assertGreater(len(self.mouse.colors), 5)
        self.assertLessEqual(len(self.gpu.colors), 2)            # 1 s of test, a 3 s interval: one color and off
        self.assertEqual(self.mouse.colors[-1], (0, 0, 0))       # black on stopping
        self.assertEqual(self.gpu.colors[-1], (0, 0, 0))         # and the GPU in its off mode

    def test_the_off_scene_is_black(self):
        s = self.service()
        self.mode(scene="off")
        try:
            for _ in range(5):
                s.cycle()
                self.t += 2
            limit = time.monotonic() + 3
            while not (self.mouse.colors and self.gpu.colors) and time.monotonic() < limit:
                time.sleep(0.01)
        finally:
            for _, e in s.emitters.values():
                e.stop(black=False)
        self.assertEqual(set(self.mouse.colors), {(0, 0, 0)})
        self.assertEqual(set(self.gpu.colors), {(0, 0, 0)})

    def test_disabling_turns_it_off_and_stops_the_thread(self):
        s = self.service()
        self.mode(scene="color", color="#FFFFFF")
        s.cycle()
        self.assertEqual(set(s.emitters), {"mouse", "gpu"})
        write(paths.control("settings.toml"), "[mouse]\nenabled = false\n\n[gpu]\nenabled = true\n")
        self.t += 2
        s.cycle()
        self.assertEqual(set(s.emitters), {"gpu"})
        self.assertEqual(self.mouse.colors[-1], (0, 0, 0))
        s.lights_out()
        self.assertEqual(s.emitters, {})

    def test_off_by_default(self):
        os.unlink(paths.control("settings.toml"))
        s = self.service()
        self.mode(scene="color", color="#FFFFFF")
        s.cycle()
        self.assertEqual(s.emitters, {})
        for name in st.DEVICES:
            self.assertIs(SETTINGS[name]["enabled"], False, name)

    def test_with_no_devices_it_touches_nothing(self):
        s = service.Service(open_output=FakeChip, clock=lambda: self.t, sleep=lambda s: None)
        self.assertEqual(s.open_device, {})
        self.assertEqual(set(service.DEVICES), set(st.DEVICES))      # main passes all three


class Brightness(unittest.TestCase):
    def test_scaling(self):
        linear = {**BLACK, "case": (1.0, 0.5, 0.0), "cooler": (0.0, 0.0, 1.0)}
        device = {"zone": "case", "brightness": 100}
        self.assertEqual(service.device_color(linear, 1.0, device, 2.2), (1.0, 0.5, 0.0))
        half = service.device_color(linear, 1.0, {**device, "brightness": 50}, 2.2)
        self.assertAlmostEqual(half[0], 0.5 ** 2.2)                  # as the eye sees it
        self.assertAlmostEqual(half[1], 0.5 * 0.5 ** 2.2)
        self.assertEqual(service.device_color(linear, 0.5, device, 2.2), (0.5, 0.25, 0.0))   # LEDs going out
        self.assertEqual(service.device_color(linear, 1.0, {**device, "brightness": 0}, 2.2), (0.0, 0.0, 0.0))
        self.assertEqual(service.device_color(linear, 1.0, {**device, "zone": "cooler"}, 2.2), (0.0, 0.0, 1.0))
        dim = {**linear, "case": (0.1, 0.05, 0.0)}
        double = service.device_color(dim, 1.0, {**device, "brightness": 200}, 2.2)
        self.assertAlmostEqual(double[0], 0.1 * 2 ** 2.2)
        self.assertAlmostEqual(double[1] / double[0], 0.5)
        top = service.device_color({**linear, "case": (0.5, 0.25, 0.0)}, 1.0, {**device, "brightness": 300}, 2.2)
        self.assertEqual(top, (1.0, 0.5, 0.0))                       # over the maximum: the same hue


class Floor(unittest.TestCase):
    def test_the_default_is_a_dim_blue(self):
        r, g, b = bytes.fromhex(KEYBOARD["floor"][1:])
        self.assertTrue(0 < r < g < b <= 12, KEYBOARD["floor"])
        for name in ("mouse", "gpu"):
            self.assertNotIn("floor", SETTINGS[name])                # only the keyboard: the mouse and GPU do go dark

    def test_in_the_dark_it_stays_on_the_floor(self):
        floor = tuple(bytes.fromhex(KEYBOARD["floor"][1:]))
        self.assertEqual(keyboard_bytes(BLACK), floor)
        self.assertEqual(keyboard_bytes({**BLACK, "case": (1.0, 0.5, 0.0)}, on=0.0), floor)
        self.assertEqual(keyboard_bytes(BLACK, device={**KEYBOARD, "brightness": 0}), floor)

    def test_without_a_floor_it_goes_dark(self):
        self.assertEqual(keyboard_bytes(BLACK, device={k: v for k, v in KEYBOARD.items() if k != "floor"}), (0, 0, 0))

    def test_above_the_floor_nothing_changes(self):
        without = {k: v for k, v in KEYBOARD.items() if k != "floor"}
        gold = {**BLACK, "case": to_linear(hex_to_rgb("#FFA420"), 0.76, 2.2)}
        self.assertEqual(service.device_color(gold, 1.0, KEYBOARD, 2.2), service.device_color(gold, 1.0, without, 2.2))

    def test_the_night_goes_down_to_the_floor_with_no_jumps(self):
        """The night blue of the sky goes out LED by LED: the keyboard comes down with it and stays on the floor."""
        blue = {**BLACK, "case": tuple(c * SETTINGS["general"]["max_brightness"] / 100
                                       for c in to_linear(hex_to_rgb("#A0B4FF"), 0.22, 2.2))}
        floor = hex_to_rgb(KEYBOARD["floor"])
        previous = None
        for i in range(101):
            color = service.device_color(blue, 1 - i / 100, KEYBOARD, 2.2)
            self.assertGreaterEqual(service.luminance(color), service.luminance(floor) * 0.999)
            if previous is not None:
                self.assertLess(max(abs(a - b) for a, b in zip(color, previous)), 0.02)
            previous = color
        self.assertEqual(to_bytes(previous), tuple(round(c * 255) for c in floor))

    def test_brighter_than_the_floor_but_another_hue(self):
        red = (0.2, 0.0, 0.0)
        self.assertEqual(service.with_floor(red, hex_to_rgb("#030408")), red)     # a dim red takes no blue


class Settings(unittest.TestCase):
    def test_defaults(self):
        for name in st.DEVICES:
            self.assertEqual(SETTINGS[name]["zone"], "case")
        self.assertEqual(SETTINGS["gpu"]["interval_s"], 3.0)
        self.assertEqual(SETTINGS["keyboard"]["refresh_s"], 0.04)

    def test_bad_values(self):
        for change, text in (({"mouse": {**SETTINGS["mouse"], "zone": "roof"}}, "mouse.zone"),
                             ({"gpu": {**SETTINGS["gpu"], "brightness": 350}}, "gpu.brightness"),
                             ({"gpu": {**SETTINGS["gpu"], "interval_s": 0.2}}, "gpu.interval_s"),
                             ({"mouse": {**SETTINGS["mouse"], "enabled": "yes"}}, "mouse.enabled"),
                             ({"keyboard": {**KEYBOARD, "floor": "blue"}}, "keyboard.floor"),
                             ({"keyboard": {**KEYBOARD, "refresh_s": 5}}, "keyboard.refresh_s")):
            with self.subTest(text=text):
                with self.assertRaisesRegex(st.InvalidSettings, text):
                    st.validate({**SETTINGS, **change})
        st.validate({**SETTINGS, "mouse": {**SETTINGS["mouse"], "floor": "#010203"}})     # any device may have a floor


class Status(unittest.TestCase):
    def test_the_status_shows_the_devices(self):
        st.write_json(paths.run("status.json"), {
            "time": time.time(), "scene": "sun", "firmware": "1.2.3.4",
            "devices": {"mouse": {"color": [255, 137, 4], "problem": None, "sends": 7},
                        "gpu": {"color": [0, 0, 0], "problem": None, "sends": 1},
                        "keyboard": {"color": None, "problem": "keyboard: not found", "sends": 0}}})
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            cli._status()
        self.assertIn("Mouse: color FF8904, 7 sends", out.getvalue())
        self.assertIn("GPU: off", out.getvalue())
        self.assertIn("Keyboard: warning: keyboard: not found", out.getvalue())


class Permissions(unittest.TestCase):
    def rules(self, name):
        return [line for line in read("system", name).splitlines() if line and not line.startswith("#")]

    def test_udev_gives_only_these_nodes(self):
        granted = [line for line in self.rules("60-luces.rules") if 'GROUP="luces", MODE="0660"' in line]
        self.assertEqual(len(granted), 3)
        self.assertIn('ATTRS{idVendor}=="048d", ATTRS{idProduct}=="5711"', granted[0])
        self.assertIn('ATTRS{idProduct}=="0099", ENV{ID_USB_INTERFACE_NUM}=="03"', granted[1])
        self.assertIn('ATTR{name}=="NVIDIA i2c adapter 1 at 1:00.0"', granted[2])
        self.assertIn('ATTRS{subsystem_device}=="0x5315"', granted[2])

    def test_the_keyboard_rule_is_apart_and_only_interface_2(self):
        granted = [line for line in self.rules("61-luces-keyboard.rules") if "GROUP=" in line]
        self.assertEqual(granted, ['SUBSYSTEM=="hidraw", ATTRS{idVendor}=="125f", ATTRS{idProduct}=="730e", '
                                   'ENV{ID_USB_INTERFACE_NUM}=="02", GROUP="luces", MODE="0660"'])
        self.assertIn("61-luces-keyboard.rules", read("system", "install.sh"))
        self.assertIn("61-luces-keyboard.rules", read("system", "uninstall.sh"))

    def test_the_unit_allows_i2c_and_nothing_else_new(self):
        unit = read("system", "luces.service")
        self.assertIn("DevicePolicy=closed\n", unit)
        self.assertEqual(sorted(line for line in unit.splitlines() if line.startswith("DeviceAllow=")),
                         ["DeviceAllow=char-hidraw rw", "DeviceAllow=char-i2c rw"])
        self.assertIn("PrivateNetwork=yes\n", unit)


if __name__ == "__main__":
    unittest.main()

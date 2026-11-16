import calendar
import os
import unittest

from luces import paths, scenes, service
from luces import settings as st
from tests.helpers import SETTINGS, SOUTH, epoch


class FakeOutput:
    info = {"firmware": "1.2.3.4"}

    def __init__(self):
        self.frames, self.started, self.closed, self.fails = [], [], [], False

    def start(self, leds):
        self.started.append(leds)

    def paint(self, frame):
        if self.fails:
            raise OSError("USB unplugged")
        self.frames.append(frame)

    def close(self):
        self.closed.append(1)


class Service(unittest.TestCase):
    def setUp(self):
        for folder in (paths.CONTROL, paths.DATA, paths.RUN):
            for f in os.listdir(folder):
                os.unlink(os.path.join(folder, f))
        self.t = calendar.timegm((2026, 11, 5, 18, 0, 0))   # a fixed instant, the same in every time zone
        self.output = FakeOutput()

    def service(self):
        return service.Service(open_output=lambda: self.output, clock=lambda: self.t, sleep=lambda s: None)

    def mode(self, **m):
        st.write_json(paths.control("mode.json"), m)

    def test_changes_scene_with_the_file(self):
        s = self.service()
        self.mode(scene="off")
        s.cycle()
        self.assertEqual(s.scene, "off")
        self.assertEqual(self.output.started, [{2: 32, 1: 32}])
        self.mode(scene="relax")
        self.t += 2
        s.cycle()
        self.assertEqual(s.scene, "relax")

    def test_rear_is_not_painted_until_it_has_a_header(self):
        linear = {z: (0.1, 0.1, 0.1) for z in scenes.ZONES}
        self.assertEqual(set(service.frame(linear, SETTINGS)), {1, 2})
        with_rear = {**SETTINGS, "zones": {**SETTINGS["zones"], "rear": {"header": 3, "leds": 32}}}
        st.validate(with_rear)
        self.assertEqual(set(service.frame(linear, with_rear)), {1, 2, 3})

    def test_a_flash_goes_above_the_smoothing(self):
        linear = {z: (0.0, 0.0, 0.0) for z in scenes.ZONES}
        r = service.with_flash(linear, {"case": 1.0}, SETTINGS, 1.0)
        self.assertGreater(r["case"][0], 0.5)
        self.assertEqual(r["cooler"], (0.0, 0.0, 0.0))
        self.assertIs(service.with_flash(linear, {}, SETTINGS, 1.0), linear)

    def test_choosing_by_hand_reaches_the_scene(self):
        with open(paths.control("place.toml"), "w") as f:
            f.write("lat = -40.0\nlon = 10.0\n")
        start = epoch(2026, 9, 1, 0, 0, 0)
        self.t = next(t for t in range(start, start + 86400, 300) if scenes.after_hours(scenes.Context(t, SETTINGS, SOUTH)))
        s = self.service()
        self.mode(scene="relax", forced_until=self.t + 3600)
        for _ in range(12):
            s.cycle()
            self.t += 1
        self.assertGreater(max(max(c) for c in self.output.frames[-1][1]), 0)

    def test_breathe_goes_back_by_itself(self):
        s = self.service()
        self.mode(scene="breathe", until=self.t + 60, back_to="relax")
        s.cycle()
        self.assertEqual(s.scene, "breathe")
        self.t += 61
        s.cycle()
        self.assertEqual(s.scene, "relax")

    def test_sends_nothing_if_nothing_changes_except_the_refresh(self):
        s = self.service()
        self.mode(scene="off")
        s.cycle()
        before = len(self.output.frames)
        for _ in range(5):
            self.t += 2
            s.cycle()
        self.assertEqual(len(self.output.frames), before)
        self.t += 61
        s.cycle()
        self.assertEqual(len(self.output.frames), before + 1)

    def test_broken_settings_keep_the_last_valid_ones(self):
        s = self.service()
        self.mode(scene="off")
        s.cycle()
        with open(paths.control("settings.toml"), "w") as f:
            f.write("[general]\nmax_brightness = 900\n")
        self.t += 2
        s.cycle()
        self.assertEqual(s.settings["general"]["max_brightness"], 70)
        self.assertIn("max_brightness", s.settings_error)

    def test_if_the_output_drops_it_retries(self):
        s = self.service()
        self.mode(scene="relax")
        s.cycle()
        self.output.fails = True
        self.t += 10
        self.assertEqual(s.cycle(), service.RETRY_S)
        self.assertIsNone(s.output)
        self.output.fails = False
        self.t += 10
        s.cycle()
        self.assertIsNotNone(s.output)

    def test_on_stop_it_paints_black(self):
        s = self.service()
        self.mode(scene="relax")
        s.cycle()
        s.lights_out()
        self.assertTrue(all(set(v) == {(0, 0, 0)} for v in self.output.frames[-1].values()))

    def test_fades_with_no_jumps(self):
        s = self.service()
        self.mode(scene="color", color="#FFFFFF")
        for _ in range(40):
            s.cycle()
            self.t += 0.25
        brightness = [max(c[1][0]) for c in self.output.frames]
        steps = [b - a for a, b in zip(brightness, brightness[1:])]
        self.assertGreater(len(brightness), 20)
        self.assertLess(max(steps), max(brightness) * 0.3)

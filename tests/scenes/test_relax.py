import calendar
import unittest

from luces import color, scenes
from luces.scenes import relax
from tests.helpers import PLACE, SETTINGS, ctx_at, distance

NOON = calendar.timegm((2026, 11, 5, 18, 0, 0))   # a fixed instant, the same in every time zone
A = SETTINGS["relax"]


def no_pulse():
    return {**SETTINGS, "relax": {**A, "pulse": {**A["pulse"], "brightness": 0.0, "tone": 0.0}}}


def series(settings, index):
    return [relax.render(scenes.Context(NOON + s, settings, started_at=NOON))["case"][index] for s in range(3600)]


class Brightness(unittest.TestCase):
    def test_stays_low_and_slow(self):
        previous = None
        for s in range(0, 1800):
            b = relax.render(scenes.Context(NOON + s, no_pulse(), PLACE, started_at=NOON))["case"][1]
            self.assertGreaterEqual(b, A["min_brightness"] / 100 - 1e-9)
            self.assertLessEqual(b, A["max_brightness"] / 100 + 1e-9)
            if previous is not None:
                self.assertLess(abs(b - previous), 0.02)
            previous = b

    def test_has_peaks_of_different_heights(self):
        b = series(no_pulse(), 1)
        peaks = [b[i] for i in range(1, 3599) if b[i - 1] < b[i] >= b[i + 1]]
        self.assertGreater(len(peaks), 40)
        self.assertGreater(max(peaks) - min(peaks), 0.08)

    def test_no_two_cycles_are_alike(self):
        b = series(no_pulse(), 1)
        peaks = [i for i in range(1, 3599) if b[i - 1] < b[i] >= b[i + 1]]
        cycles = [y - x for x, y in zip(peaks, peaks[1:]) if y - x > 20]
        self.assertGreater(max(cycles) - min(cycles), 20)

    def test_the_pulse_is_subtle_but_real(self):
        start = NOON - 3600
        flat = {**SETTINGS, "relax": {**A, "min_brightness": 25, "max_brightness": 25}}   # only the pulse
        b = [relax.render(scenes.Context(NOON + s * 0.2, flat, started_at=start))["case"][1] for s in range(60)]
        self.assertGreater(max(b) / min(b), 1.2)
        self.assertLess(max(b) / min(b), 1.3)


class Color(unittest.TestCase):
    def _colors(self):
        return [relax.render(ctx_at(NOON + s * 5, started_at=NOON))["case"][0] for s in range(1440)]

    def test_blue_never_dominates(self):
        for rgb in self._colors():
            self.assertLess(rgb[2], max(rgb[0], rgb[1]))

    def test_goes_from_green_to_white(self):
        colors = self._colors()
        green, white = (color.hex_to_rgb(A["palette"][i]) for i in (0, -1))
        self.assertLess(min(distance(c, green) for c in colors), 0.25)
        self.assertLess(min(distance(c, white) for c in colors), 0.25)

    def test_the_color_never_stops(self):
        colors = series(no_pulse(), 0)
        for i in range(0, 3540, 10):
            window = colors[i:i + 60]
            self.assertGreater(max(distance(window[0], c) for c in window), 0.03, i)   # within a minute it always changed
        self.assertLess(max(distance(p, q) for p, q in zip(colors, colors[1:])), 0.1)

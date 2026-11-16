import math
import time
import unittest

from luces import color, scenes, service
from luces.scenes import sun
from tests.helpers import SETTINGS, autocorrelation, band_power, correlation, ctx_at, distance

NOON = time.mktime((2026, 11, 5, 15, 0, 0, 0, 0, -1))
STEP = sun.SCENE.frame_s
A = SETTINGS["sun"]


def one_hour():
    solar = {"fetched": NOON, "flux": 111, "sunspots": 64, "c": 3, "m": 0, "x": 0}
    return [sun.render(scenes.Context(NOON + s, SETTINGS, solar=solar))["case"] for s in range(3600)]


def fire_only(seconds, flux=124, zone="case"):
    """The color and brightness of a zone frame by frame, with no sunspots or flares: just the fire."""
    solar = {"fetched": NOON, "flux": flux, "sunspots": 0, "c": 0, "m": 0, "x": 0}
    settings = {**SETTINGS, "sun": {**A, "sunspots": {**A["sunspots"], "base": 0.0}, "flares": {**A["flares"], "base": 0.0}}}
    return [sun.render(scenes.Context(NOON + i * STEP, settings, solar=solar))[zone] for i in range(int(seconds / STEP))]


class Colors(unittest.TestCase):
    def test_goes_through_the_shades_of_orange(self):
        greens = sorted(rgb[1] for rgb, _ in one_hour())
        self.assertLess(greens[0], 0.12)
        self.assertGreater(greens[-1], 0.6)
        self.assertGreater(greens[len(greens) * 9 // 10] - greens[len(greens) // 10], 0.15)

    def test_has_black_parts_and_yellow_bursts(self):
        series = one_hour()
        dark = A["brightness"] / 100 * 0.4
        self.assertGreater(sum(1 for _, b in series if b < dark), 30)
        yellow = color.hex_to_rgb(A["flare"])
        bursts = [i for i, (rgb, _) in enumerate(series) if distance(rgb, yellow) < 0.2]
        self.assertGreater(len(bursts), 30)
        self.assertGreater(bursts[-1] - bursts[0], 1200)   # spread out, not all together

    def test_the_brightest_is_the_yellowest(self):
        series = fire_only(120)
        self.assertGreater(correlation([rgb[1] for rgb, _ in series], [b for _, b in series]), 0.8)


class Motion(unittest.TestCase):
    def test_frames_are_fast_enough_for_the_tongues(self):
        self.assertLessEqual(sun.SCENE.frame_s, 0.1)   # under 10 frames a second, fire looks jumpy
        self.assertLessEqual(sun.SCENE.smoothing_s, 0.1)

    def test_tongues_rise_fast_and_fall_slowly(self):
        b = [v for _, v in fire_only(300)]
        tongues = [i for i in range(2, len(b) - 2) if b[i] - min(b[i - 2:i + 3]) > 0.02 and b[i] == max(b[i - 2:i + 3])]
        self.assertTrue(0.7 < len(tongues) / 300 < 3, len(tongues))
        rises = [y - x for x, y in zip(b, b[1:]) if y > x]
        falls = [x - y for x, y in zip(b, b[1:]) if y < x]
        self.assertGreater(sum(rises) / len(rises), 1.3 * sum(falls) / len(falls))

    def test_has_the_spectrum_of_a_flame(self):
        """Above its rhythm it falls as 1/f^n: flames measure n = 2.12 ± 0.7."""
        b = [v for _, v in fire_only(300)]
        n = math.log10(band_power(b, STEP, 3, 3.5) / band_power(b, STEP, 6, 7)) / math.log10(6.5 / 3.25)
        self.assertTrue(1.4 < n < 2.8, n)

    def test_is_not_a_metronome(self):
        b = [v for _, v in fire_only(300)]
        self.assertLess(band_power(b, STEP, 2.0, 2.4), 2 * band_power(b, STEP, 1.2, 1.6))

    def test_has_no_rhythm_the_eye_can_catch(self):
        solar = {"fetched": 1.79e9, "flux": 130, "sunspots": 60, "c": 3, "m": 0, "x": 0}
        series = [sun.render(scenes.Context(1.79e9 + s, SETTINGS, solar=solar))["case"][1] for s in range(7200)]
        for lag in range(40, 1800, 20):   # a cycle would look like itself again at some lag
            self.assertLess(abs(autocorrelation(series, lag)), 0.45, lag)

    def test_the_fire_moves_from_one_zone_to_the_next(self):
        case = [b for _, b in fire_only(120)]
        cooler = [b for _, b in fire_only(120, zone="cooler")]
        delay = round(A["travel_s"] / STEP)
        self.assertGreater(correlation(case[:-delay], cooler[delay:]), correlation(case, cooler) + 0.1)

    def test_moves_more_with_more_activity(self):
        def movement(flux):
            b = [v for _, v in fire_only(300, flux)]
            mean = sum(b) / len(b)
            return math.sqrt(sum((x - mean) ** 2 for x in b) / len(b))
        self.assertGreater(movement(190), movement(75) * 1.15)

    def test_the_same_instant_gives_the_same_result(self):
        c = ctx_at(NOON + 1234.5)
        self.assertEqual(sun.render(c), sun.render(c))


class SolarData(unittest.TestCase):
    def test_works_without_data(self):
        c = scenes.Context(NOON, SETTINGS)
        self.assertEqual(sun.activity(c), A["activity_without_data"])
        c.solar = {"fetched": NOON - 100 * 3600, "flux": 200}
        self.assertEqual(sun.activity(c), A["activity_without_data"])


def worst_second(values, threshold):
    """The worst second: a flash is two opposing changes of at least `threshold`."""
    turns, high, low, direction = [], values[0], values[0], 0
    for i, v in enumerate(values):
        high, low = max(high, v), min(low, v)
        if direction >= 0 and high - v >= threshold:
            turns.append(i)
            direction, high, low = -1, v, v
        elif direction <= 0 and v - low >= threshold:
            turns.append(i)
            direction, high, low = 1, v, v
    frames = 1 / STEP
    return max((sum(1 for g in turns[k:k + 8] if g - i < frames) / 2 for k, i in enumerate(turns)), default=0.0)


class Flashes(unittest.TestCase):
    def test_the_counter_sees_a_fast_flicker(self):
        square = [float((i // 2) % 2) for i in range(600)]   # 3.8 Hz
        self.assertGreater(worst_second(square, 0.1), 3)

    def test_never_more_than_3_flashes_a_second(self):
        """The limit of WCAG 2.3.1, with the Sun in a storm. For red it uses the rule of WCAG 2.0, which counts any change
        of red: the current one also asks for a change of hue, and between oranges there is hardly any. It measures the
        light that leaves the service, not what the scene asks for."""
        solar = {"fetched": NOON, "flux": 250, "sunspots": 300, "c": 30, "m": 10, "x": 3}
        fade, red, light = service.Fade(), [], []
        for i in range(int(900 / STEP)):
            target = service.linear_target(sun.render(ctx_at(NOON + i * STEP, solar=solar)), SETTINGS, 1.0)
            r, g, b = fade.step(target, STEP, sun.SCENE.smoothing_s)["case"]
            red.append(r - g - b)
            light.append(0.2126 * r + 0.7152 * g + 0.0722 * b)
        self.assertLessEqual(worst_second(red, 20 / 320), 3)
        self.assertLessEqual(worst_second(light, 0.1), 3)

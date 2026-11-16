import unittest

from luces.physics.fire import Campfire, Embers, Gusts, Restlessness, Tongues
from tests.helpers import band_power


def mean_step(pattern, step_s=0.066, seconds=300):
    values = [pattern(1.79e9 + i * step_s) for i in range(int(seconds / step_s))]
    return sum(abs(a - b) for a, b in zip(values, values[1:])) / len(values)


class EachPatternWorksAlone(unittest.TestCase):
    def test_ranges(self):
        for pattern, low, high in ((Embers(), 0, 1), (Gusts(), 0, 1), (Restlessness(), 0.5, 1.5), (Tongues(), 0, 2)):
            values = [pattern(1.79e9 + i * 0.1) for i in range(3000)]
            self.assertGreaterEqual(min(values), low, pattern)
            self.assertLessEqual(max(values), high, pattern)

    def test_the_same_instant_gives_the_same_value(self):
        for pattern in (Embers(), Gusts(), Restlessness(), Tongues()):
            self.assertEqual(pattern(1234.5), pattern(1234.5))

    def test_each_rhythm_is_faster_than_the_last(self):
        self.assertLess(mean_step(Embers()), mean_step(Gusts()))
        self.assertLess(mean_step(Gusts()), mean_step(Tongues()))

    def test_parameters_change_the_rhythm(self):
        self.assertGreater(mean_step(Tongues(every_s=0.45)), mean_step(Tongues(every_s=1.5)))


class TongueShape(unittest.TestCase):
    def test_rise_fast_and_fall_slowly(self):
        values = [Tongues()(1.79e9 + i * 0.02) for i in range(15000)]
        rises = [b - a for a, b in zip(values, values[1:]) if b > a]
        falls = [a - b for a, b in zip(values, values[1:]) if b < a]
        self.assertGreater(sum(rises) / len(rises), 2 * sum(falls) / len(falls))

    def test_spectrum_falls_like_a_flame(self):
        """Above their rhythm, flames fall as 1/f^n, with n = 2.12 ± 0.7 as measured."""
        step = 0.066
        values = [Tongues()(1.79e9 + i * step) for i in range(4500)]
        import math
        n = math.log10(band_power(values, step, 3, 3.5) / band_power(values, step, 6, 7)) / math.log10(6.5 / 3.25)
        self.assertTrue(1.4 < n < 2.8, n)


class CampfireCombines(unittest.TestCase):
    def test_heat_and_size_stay_in_range(self):
        fire = Campfire()
        for i in range(3000):
            flame = fire.at(1.79e9 + i * 0.1, strength=2.0, zone=i % 3, delay_s=0.3 * (i % 3))
            self.assertTrue(0 <= flame.heat <= 1)
            self.assertTrue(0 <= flame.size <= 1)

    def test_more_strength_gives_more_heat(self):
        fire = Campfire()
        weak = sum(fire.at(1.79e9 + i * 0.1, 0.5).heat for i in range(2000))
        strong = sum(fire.at(1.79e9 + i * 0.1, 1.5).heat for i in range(2000))
        self.assertGreater(strong, weak)

    def test_patterns_can_be_swapped(self):
        slow = Campfire(tongues=Tongues(every_s=2.0))
        self.assertNotEqual(slow.at(1.79e9), Campfire().at(1.79e9))

import unittest

from luces.physics.breathing import breath_shape, breaths_taken


class Shape(unittest.TestCase):
    def test_rises_and_falls_without_corners(self):
        self.assertAlmostEqual(breath_shape(0, 3, 7), 0)
        self.assertAlmostEqual(breath_shape(3, 3, 7), 1)
        self.assertAlmostEqual(breath_shape(10, 3, 7), 0)


class Slowdown(unittest.TestCase):
    def _breaths(self, first_min, last_min):
        return breaths_taken(last_min * 60, 5.0, 10.0, 720.0) - breaths_taken(first_min * 60, 5.0, 10.0, 720.0)

    def test_slows_down_little_by_little_to_six_a_minute(self):
        self.assertAlmostEqual(self._breaths(0, 1), 11.5, delta=1)
        self.assertAlmostEqual(self._breaths(30, 31), 6, delta=0.01)
        per_minute = [self._breaths(m, m + 1) for m in range(13)]
        self.assertEqual(per_minute, sorted(per_minute, reverse=True))

    def test_does_not_jump(self):
        breaths = [breaths_taken(s, 5.0, 10.0, 720.0) for s in range(0, 1200)]
        self.assertLess(max(b - a for a, b in zip(breaths, breaths[1:])), 0.21)
        self.assertGreater(min(b - a for a, b in zip(breaths, breaths[1:])), 0.09)

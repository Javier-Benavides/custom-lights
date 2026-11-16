import unittest

from luces.physics.noise import even_noise, fractal_noise, swells


class FractalNoise(unittest.TestCase):
    def test_stays_between_minus_one_and_one_and_does_not_jump(self):
        values = [fractal_noise(1.79e9 + s * 0.25, 9.0, 1) for s in range(20000)]
        self.assertLessEqual(max(abs(v) for v in values), 1.0)
        self.assertLess(max(abs(a - b) for a, b in zip(values, values[1:])), 0.25)
        self.assertGreater(max(values) - min(values), 0.8)

    def test_same_instant_same_value(self):
        self.assertEqual(fractal_noise(1234.5, 9.0, 3), fractal_noise(1234.5, 9.0, 3))
        self.assertNotEqual(fractal_noise(1234.5, 9.0, 3), fractal_noise(1234.5, 9.0, 4))


class EvenNoise(unittest.TestCase):
    def test_spends_the_same_time_at_every_value(self):
        values = [even_noise(1.79e9 + s * 3.0, 40.0, 23) for s in range(30000)]
        for limit in (0.25, 0.5, 0.75):
            self.assertAlmostEqual(sum(1 for v in values if v < limit) / len(values), limit, delta=0.03)


class Swells(unittest.TestCase):
    def test_stays_between_zero_and_one(self):
        values = [swells(s * 1.0, 55.0, 0.4, 41) for s in range(5000)]
        self.assertGreaterEqual(min(values), 0.0)
        self.assertLessEqual(max(values), 1.0)
        self.assertGreater(max(values) - min(values), 0.5)

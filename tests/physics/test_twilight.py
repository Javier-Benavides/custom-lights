import unittest

from luces.physics.twilight import Stage, leds_at, sky_at

TABLE = [Stage(-8, (0, 0, 1), 20, 0.0), Stage(-5, (0, 0, 1), 20, 1.0), Stage(5, (1, 0.5, 0), 80), Stage(12, (0, 0.5, 1), 60)]


class Twilight(unittest.TestCase):
    def test_blends_between_stages(self):
        rgb, brightness = sky_at(TABLE, 0)
        self.assertEqual(rgb, (0.5, 0.25, 0.5))
        self.assertAlmostEqual(brightness, 0.5)

    def test_stops_at_both_ends(self):
        self.assertEqual(sky_at(TABLE, -30), ((0, 0, 1), 0.2))
        self.assertEqual(sky_at(TABLE, 60), ((0, 0.5, 1), 0.6))

    def test_leds_go_out_without_changing_the_color(self):
        self.assertEqual(sky_at(TABLE, -7), sky_at(TABLE, -5))
        self.assertAlmostEqual(leds_at(TABLE, -6.5), 0.5)
        self.assertEqual(leds_at(TABLE, -30), 0.0)
        self.assertEqual(leds_at(TABLE, 30), 1.0)

import unittest

from luces.physics import storm


class Strikes(unittest.TestCase):
    def test_a_strike_is_short_and_has_at_most_three_strokes(self):
        for _, _, strokes in storm.strikes_in_hour(500000, 200.0):
            self.assertLessEqual(len(strokes), 3)
            self.assertLess(strokes[-1][0], 1.0)

    def test_the_rate_is_respected(self):
        self.assertAlmostEqual(sum(len(storm.strikes_in_hour(h, 20.5)) for h in range(500)) / 500, 20.5, delta=0.1)


class Flash(unittest.TestCase):
    STRIKE = ((1000.0, 1, ((0.0, 1.0), (0.2, 0.8))),)

    def test_is_born_in_a_zone_and_reaches_the_others_weaker(self):
        lit = storm.flash_at(1000.04, self.STRIKE, 0.06)
        self.assertGreater(lit[1], lit[0])
        self.assertEqual(lit[0], lit[2])

    def test_fades_within_a_moment(self):
        self.assertEqual(storm.flash_at(1001.5, self.STRIKE, 0.06), {})
        self.assertEqual(storm.flash_at(999.0, self.STRIKE, 0.06), {})

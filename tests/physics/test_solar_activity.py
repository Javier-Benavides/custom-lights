import unittest

from luces.physics import solar_activity as sa


class Activity(unittest.TestCase):
    def test_goes_from_quiet_to_active(self):
        self.assertEqual(sa.activity_from_flux(70, 70, 200), 0)
        self.assertEqual(sa.activity_from_flux(200, 70, 200), 1)
        self.assertEqual(sa.activity_from_flux(500, 70, 200), 1)


class Events(unittest.TestCase):
    def test_many_small_and_few_big(self):
        strengths = [e[2] for h in range(400) for e in sa.events_in_hour(h, 5.0, 2)]
        small = sum(1 for s in strengths if s < 0.3)
        big = sum(1 for s in strengths if s >= 0.9)
        self.assertGreater(small, big * 2)
        self.assertGreater(big, 0)

    def test_rate_is_respected(self):
        self.assertAlmostEqual(sum(len(sa.events_in_hour(h, 7.5, 1)) for h in range(1000)) / 1000, 7.5, delta=0.1)

    def test_events_near_only_gives_recent_ones(self):
        t = 1.79e9
        for start, _, _ in sa.events_near(t, 30.0, 1, 100.0):
            self.assertTrue(t - 100.0 <= start <= t)


class Shapes(unittest.TestCase):
    def test_a_flare_rises_fast_and_falls_slowly(self):
        self.assertEqual(sa.flare_shape(-1, 2, 8), 0)
        self.assertAlmostEqual(sa.flare_shape(2, 2, 8), 1)
        self.assertAlmostEqual(sa.flare_shape(10, 2, 8), 0.3679, places=3)
        self.assertEqual(sa.flare_shape(100, 2, 8), 0)

    def test_a_sunspot_comes_and_goes(self):
        self.assertEqual(sa.sunspot_shape(0, 30), 0)
        self.assertAlmostEqual(sa.sunspot_shape(15, 30), 1)
        self.assertEqual(sa.sunspot_shape(31, 30), 0)

    def test_an_event_reaches_other_zones_weaker_and_later(self):
        events = ((0.0, 0, 1.0),)
        here = sa.flare_at(2.0, 0, events, 2.0, 8.0)
        there = sa.flare_at(2.0, 1, events, 2.0, 8.0)
        self.assertGreater(here, there)
        self.assertEqual(sa.sunspot_at(5.0, 2, events, 30.0), 0)

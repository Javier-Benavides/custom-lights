import calendar
import unittest

from luces import scenes
from luces.physics.sun_position import HORIZON, sun_altitude
from tests.helpers import SETTINGS, SOUTH, epoch

NOON = calendar.timegm((2026, 11, 5, 18, 0, 0))   # a fixed instant, the same in every time zone


def after_hours(t):
    return scenes.after_hours(scenes.Context(t, SETTINGS, SOUTH))


def first_off_moment():
    start = epoch(2026, 9, 1, 0, 0, 0)
    return next(t for t in range(start, start + 86400, 300) if after_hours(t))


class Schedule(unittest.TestCase):
    def _off_hour(self, *date):
        start = epoch(*date, 12, 0, 0)
        for m in range(0, 1440):
            if after_hours(start + m * 60):
                return m / 60
        self.fail("it never went off")

    def test_changes_with_the_seasons(self):
        self.assertGreater(self._off_hour(2026, 12, 21) - self._off_hour(2026, 6, 21), 2.0)

    def test_goes_off_after_sunset_and_on_at_sunrise(self):
        start = epoch(2026, 9, 1, 0, 0, 0)
        states = [(t, after_hours(t)) for t in range(start, start + 86400, 300)]
        for t, off in states:
            if sun_altitude(t, SOUTH["lat"], SOUTH["lon"]) >= HORIZON:
                self.assertFalse(off)
        self.assertTrue(any(off for _, off in states))

    def test_just_after_sunset_it_stays_on(self):
        """With wrong rounding, the first minutes after sunset were taken for yesterday's sunset."""
        start = epoch(2026, 9, 1, 12, 0, 0)
        sunset = next(t for t in range(start, start + 86400, 30) if sun_altitude(t, SOUTH["lat"], SOUTH["lon"]) < HORIZON)
        for t in range(sunset, sunset + 2 * 3600, 30):
            self.assertFalse(after_hours(t))
        self.assertTrue(after_hours(sunset + 3 * 3600 + 60))

    def test_puts_sun_and_relax_out(self):
        t = first_off_moment()
        for name in ("sun", "relax"):
            self.assertEqual(scenes.render(name, scenes.Context(t, SETTINGS, SOUTH))["case"][1], 0)

    def test_choosing_by_hand_beats_the_schedule(self):
        t = first_off_moment()
        for name in ("sun", "relax"):
            c = scenes.Context(t, SETTINGS, SOUTH, forced_until=t + 3600)
            self.assertGreater(scenes.render(name, c)["case"][1], 0)
            c.forced_until = t - 1
            self.assertEqual(scenes.render(name, c)["case"][1], 0)

    def test_no_place_means_no_schedule(self):
        self.assertGreater(scenes.render("relax", scenes.Context(NOON, SETTINGS))["case"][1], 0)

    def test_breathe_ignores_the_schedule(self):
        t = first_off_moment()
        self.assertGreater(scenes.render("breathe", scenes.Context(t, SETTINGS, SOUTH, started_at=t))["case"][1], 0)

    def test_breathing_is_six_a_minute_with_a_long_exhale(self):
        b = SETTINGS["breathe"]
        self.assertEqual(60 / (b["inhale_s"] + b["exhale_s"]), 6)
        self.assertLess(b["inhale_s"] / b["exhale_s"], 0.5)

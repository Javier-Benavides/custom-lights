import unittest

from luces.physics import sun_position as sp
from tests.helpers import SOUTH, epoch


class Altitude(unittest.TestCase):
    def test_solstice_at_the_equator(self):
        best = max(sp.sun_altitude(epoch(2026, 6, 21, 11, m, 0), 0.0, 0.0) for m in range(0, 60))
        best = max(best, max(sp.sun_altitude(epoch(2026, 6, 21, 12, m, 0), 0.0, 0.0) for m in range(0, 60)))
        self.assertAlmostEqual(best, 66.56, delta=0.2)

    def test_equinox_at_the_equator(self):
        best = max(sp.sun_altitude(epoch(2026, 3, 20, 12, m, 0), 0.0, 0.0) for m in range(0, 60))
        self.assertGreater(best, 89.0)

    def test_night_at_the_antimeridian(self):
        self.assertLess(sp.sun_altitude(epoch(2026, 3, 20, 0, 0, 0), 0.0, 0.0), -80)


class Crossing(unittest.TestCase):
    def test_gives_the_time_of_an_altitude(self):
        noon = max(range(1793847600, 1793847600 + 86400, 60), key=lambda t: sp.sun_altitude(t, 10.0, 20.0))
        t = sp.crossing(noon, noon + 43200, 5.0, 10.0, 20.0)
        self.assertAlmostEqual(sp.sun_altitude(t, 10.0, 20.0), 5.0, places=2)
        self.assertIsNone(sp.crossing(noon, noon + 3600, -30.0, 10.0, 20.0))

    def test_twilight_lasts_longer_away_from_the_equinoxes(self):
        """The time comes from the altitude: in winter the Sun sets at a slant and each stage lasts longer."""
        def minutes(t0, lat):
            noon = max(range(t0, t0 + 86400, 300), key=lambda t: sp.sun_altitude(t, lat, 0.0))
            end = noon + 43200
            return (sp.crossing(noon, end, -8, lat, 0.0) - sp.crossing(noon, end, 12, lat, 0.0)) / 60
        self.assertGreater(minutes(1782000000, -35.0), minutes(1774051200, -35.0) + 5)


class LastSunset(unittest.TestCase):
    def test_is_a_sunset(self):
        t = epoch(2026, 9, 1, 23, 0, 0)
        sunset = sp.last_sunset(t, SOUTH["lat"], SOUTH["lon"])
        self.assertLess(t - sunset, 86400)
        self.assertGreater(sp.sun_altitude(sunset - 300, SOUTH["lat"], SOUTH["lon"]), sp.HORIZON)
        self.assertLess(sp.sun_altitude(sunset + 300, SOUTH["lat"], SOUTH["lon"]), sp.HORIZON)

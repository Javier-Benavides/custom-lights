import unittest

from luces.physics.sky_model import Atmosphere, rayleigh, to_hex


class SkyModel(unittest.TestCase):
    def test_short_wavelengths_scatter_more(self):
        self.assertAlmostEqual(rayleigh(400) / rayleigh(800), 16.0)

    def test_the_zenith_is_blue_by_day(self):
        a = Atmosphere()
        r, g, b = a.to_rgb(a.sky_spectrum(45, 90, 0))[0]
        self.assertGreater(b, g)
        self.assertGreater(g, r)

    def test_a_low_sun_is_redder_than_a_high_one(self):
        a = Atmosphere()
        low, high = a.to_rgb(a.direct_spectrum(1, 6))[0], a.to_rgb(a.direct_spectrum(45, 6))[0]
        self.assertGreater(low[0] / low[2], high[0] / high[2])

    def test_the_earth_shadow_cuts_direct_light(self):
        a = Atmosphere()
        self.assertEqual(set(a.direct_spectrum(-5, 3)), {0.0})
        self.assertGreater(max(a.direct_spectrum(-1, 6)), 0)

    def test_to_hex_scales_to_full(self):
        self.assertEqual(to_hex((0.5, 0.5, 0.5)), "#FFFFFF")

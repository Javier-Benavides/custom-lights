import unittest

from luces import color, scenes, service
from tests.helpers import SETTINGS


class Leds(unittest.TestCase):
    def test_the_service_puts_out_the_requested_share_in_each_zone(self):
        linear = {z: (0.5, 0.5, 0.5) for z in scenes.ZONES}
        for leds in service.frame(linear, SETTINGS, 0.5).values():
            self.assertEqual(sum(1 for led in leds[:8] if any(led)), 4)

    def test_all_on_changes_nothing(self):
        self.assertEqual(color.quantize((0.3, 0.2, 0.1), 32, 1.0), color.quantize((0.3, 0.2, 0.1), 32))

    def test_they_go_out_one_by_one_and_far_from_the_last(self):
        for n in range(9):
            leds = color.quantize((0.5, 0.5, 0.5), 8, n / 8)
            self.assertEqual(sum(1 for led in leds if any(led)), n)
        order = color.OFF_ORDER
        self.assertEqual(sorted(order), list(range(8)))
        for a, b in zip(order, order[1:]):
            self.assertGreater(min((a - b) % 8, (b - a) % 8), 1)

    def test_each_led_fades_with_the_same_hue(self):
        leds = color.quantize((0.4, 0.2, 0.8), 8, 7.5 / 8)
        fading = leds[color.OFF_ORDER[0]]
        self.assertGreater(fading[2], 90)
        self.assertLess(fading[2], 110)
        self.assertAlmostEqual(fading[0] / fading[2], 0.5, delta=0.03)

    def test_black_is_exactly_black(self):
        self.assertEqual(color.quantize((0.0, 0.0, 0.0), 8), [(0, 0, 0)] * 8)

    def test_at_low_brightness_every_led_has_the_same_color(self):
        """Bytes such as (1, 0, 1), (0, 1, 1) and (0, 0, 1) looked pink, green and blue on the same fan."""
        blue = color.hex_to_rgb("#A0B4FF")
        for brightness in (0.22, 0.18, 0.14, 0.10, 0.06):
            linear = tuple(c * 0.7 for c in color.to_linear(blue, brightness, 2.2))
            self.assertEqual(len(set(color.quantize(linear, 32))), 1, brightness)

    def test_at_low_brightness_the_hue_does_not_drift_to_green(self):
        blue = color.hex_to_rgb("#A0B4FF")
        for tenths in range(1, 100):
            r, g, b = color.to_bytes(tuple(c * 0.7 * tenths / 100 for c in color.to_linear(blue, 0.22, 2.2)))
            self.assertGreaterEqual(b, g)
            if b == 1:
                self.assertEqual((r, g), (0, 0))   # with a single step of light, only blue

    def test_to_bytes_keeps_white_and_extremes(self):
        self.assertEqual(color.to_bytes((1.0, 1.0, 1.0)), (255, 255, 255))
        self.assertEqual(color.to_bytes((0.0, 0.0, 0.0)), (0, 0, 0))
        self.assertEqual(color.to_bytes((2.0, -1.0, 0.5)), (255, 0, 128))


class Light(unittest.TestCase):
    def test_gamma(self):
        self.assertAlmostEqual(color.to_linear((1, 1, 1), 0.5, 2.0)[0], 0.25)

    def test_brightness_limit(self):
        r = {"case": ((1.0, 1.0, 1.0), 1.0), "cooler": ((1.0, 1.0, 1.0), 1.0)}
        self.assertAlmostEqual(service.linear_target(r, SETTINGS, 1.0)["case"][0], 0.7)

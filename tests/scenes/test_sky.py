import dataclasses
import unittest

from luces import color, scenes
from luces.physics import twilight
from luces.physics.sun_position import sun_altitude
from luces.scenes import demo, sky
from tests.helpers import PLACE, SETTINGS, ctx_at, distance, one_day

WEATHER = SETTINGS["sky"]["weather"]


def altitude_at(t):
    return sun_altitude(t, PLACE["lat"], PLACE["lon"])


def daytime():
    return next(t for t in one_day() if altitude_at(t) > 30)


def fixed(altitude, rising=False, t=None, **extra):
    return scenes.Context(daytime() if t is None else t, SETTINGS, PLACE, fixed_sun=(altitude, rising), **extra)


def stage(altitude, rising=False):
    return sky.render(fixed(altitude, rising))["case"][0]


def overcast(t, coverage=1.0, **extra):
    return {"time": t, "coverage": coverage, "kind": None, **extra}


class DayAndNight(unittest.TestCase):
    def test_night_is_off_and_day_is_blue(self):
        days = nights = 0
        for t in one_day():
            altitude = altitude_at(t)
            r = sky.render(ctx_at(t))
            if altitude < -9.5:
                self.assertEqual(r["case"][1], 0)
                nights += 1
            elif altitude > 12:
                rgb, brightness = r["case"]
                self.assertGreater(rgb[2], rgb[0])
                self.assertAlmostEqual(brightness, 0.6, delta=0.6 * 0.2)   # the sky moves, but around the stage
                days += 1
        self.assertGreater(days, 60)
        self.assertGreater(nights, 60)

    def test_red_wins_at_sunset(self):
        for t in one_day():
            if -1 < altitude_at(t) < 3:
                rgb = sky.render(ctx_at(t))["case"][0]
                self.assertGreater(rgb[0], rgb[2])

    def test_a_clear_sky_does_not_stay_fixed(self):
        t = daytime()
        samples = [sky.render(ctx_at(t + s))["case"] for s in range(0, 600, 10)]
        brightness = [m[1] for m in samples]
        self.assertGreater(max(brightness) - min(brightness), 0.04)
        self.assertLess(max(brightness) - min(brightness), 0.25)
        self.assertGreater(len({round(m[0][0], 3) for m in samples}), 10)

    def test_the_whole_day_has_no_jumps(self):
        previous = None
        for t in (daytime() - 43200 + s * 60 for s in range(1440)):
            r = sky.render(ctx_at(t))
            on = scenes.leds_on("sky", ctx_at(t))   # at the end, the light drops by putting LEDs out
            now = {z: tuple(c * b * on for c in rgb) for z, (rgb, b) in r.items()}
            if previous:
                for z in scenes.ZONES:
                    self.assertLess(distance(now[z], previous[z]), 0.2)
            previous = now

    def test_without_a_place_it_stays_off(self):
        self.assertEqual(sky.render(scenes.Context(0.0, SETTINGS))["case"][1], 0)


class Weather(unittest.TestCase):
    def test_rain_is_dimmer_and_gray(self):
        t = daytime()
        r = sky.render(ctx_at(t, weather={"time": t, "coverage": 1.0, "kind": "rain"}))["case"]
        self.assertLessEqual(r[1], 0.32 * 1.2)
        self.assertLess(distance(r[0], color.hex_to_rgb(WEATHER["rain"]["color"])), 0.2)

    def test_clouds_move_towards_white(self):
        t = daytime()
        clear = sky.render(ctx_at(t))["case"][0]
        cloudy = sky.render(ctx_at(t, weather=overcast(t)))["case"][0]
        self.assertGreater(cloudy[0], clear[0])

    def test_overcast_is_white(self):
        t = daytime()
        white = color.hex_to_rgb(WEATHER["white"])
        near = [distance(sky.render(ctx_at(t + s, weather=overcast(t)))["case"][0], white) for s in range(0, 600, 5)]
        self.assertLess(min(near), 0.05)
        self.assertLess(max(near), 0.3)

    def test_a_cloud_crosses_from_case_to_cooler(self):
        t = daytime()
        weather = overcast(t, 0.5)
        before = sky.render(ctx_at(t, weather=weather))["case"]
        after = sky.render(ctx_at(t + WEATHER["zone_delay_s"], weather=weather))["cooler"]
        self.assertLess(distance(before[0], after[0]), 0.01)

    def test_with_a_low_sun_a_cloud_does_not_turn_white(self):
        for t in one_day():
            if 0.5 < altitude_at(t) < 2:
                r = sky.render(ctx_at(t, weather=overcast(t)))["case"][0]
                self.assertGreater(distance(r, color.hex_to_rgb(WEATHER["white"])), 0.1)
                return
        self.fail("no low Sun on the test day")

    def test_old_data_is_ignored(self):
        t = daytime()
        self.assertEqual(sky.render(ctx_at(t)), sky.render(ctx_at(t, weather={"time": t - 4 * 3600, "coverage": 1.0, "kind": "rain"})))

    def test_afterglow_with_clouds_and_a_low_sun(self):
        t = daytime()
        r = sky.render(fixed(-1.0, t=t, weather=overcast(t)))["cooler"][0]
        self.assertLess(distance(r, color.hex_to_rgb(WEATHER["afterglow"])), distance(r, color.hex_to_rgb(WEATHER["white"])))

    def test_a_high_cloud_stays_lit_when_a_low_one_does_not(self):
        t = daytime()

        def cloud(km):
            return sky.render(fixed(-1.5, t=t, weather=overcast(t, cloud_height_km=km)))["cooler"][0]
        low, high = cloud(1.5), cloud(9.0)
        self.assertGreater(high[0] - high[2], low[0] - low[2])

    def test_with_no_cloud_height_it_uses_the_settings(self):
        t = daytime()
        without = sky.render(fixed(-1.5, t=t, weather=overcast(t)))["cooler"]
        with_it = sky.render(fixed(-1.5, t=t, weather=overcast(t, cloud_height_km=WEATHER["cloud_height_km"])))["cooler"]
        self.assertEqual(without, with_it)


class Twilight(unittest.TestCase):
    """The altitudes here come from comparing the scene with photos of a real sunset. See docs/physics/twilight.md."""

    def test_sunset_goes_from_gold_to_reddish_to_blue(self):
        gold, reddish = stage(4), stage(-1)
        self.assertGreater(gold[1], reddish[1])
        blue = stage(-5)
        self.assertGreater(blue[2], blue[1])
        self.assertGreater(blue[1], blue[0])   # more green than red, or it turns lilac

    def test_at_the_end_the_leds_go_out_without_changing_the_blue(self):
        table = sky.stages(SETTINGS["sky"]["sunset"])
        t = daytime()

        def at(altitude):
            return twilight.sky_at(table, altitude), scenes.leds_on("sky", fixed(altitude, t=t))
        start, middle, almost = at(-5.0), at(-6.5), at(-7.9)
        self.assertEqual(start[0], middle[0])
        self.assertEqual(start[0], almost[0])
        self.assertEqual(start[1], 1.0)
        self.assertAlmostEqual(middle[1], 0.5)
        self.assertLess(almost[1], 0.05)
        self.assertGreater(sky.render(fixed(-7.9, t=t))["case"][1], 0)
        self.assertEqual(sky.render(fixed(-8.1, t=t))["case"][1], 0)

    def test_by_day_all_leds_are_on_and_in_other_scenes_too(self):
        self.assertEqual(scenes.leds_on("sky", fixed(30.0, True)), 1.0)
        self.assertEqual(scenes.leds_on("sun", fixed(-7.0)), 1.0)

    def test_sunrise_and_sunset_go_in_unison(self):
        t = daytime()
        weather = overcast(t, 0.5)
        for altitude in (-7, -3, -1, 1, 4, 8):
            for rising in (True, False):
                for s in range(0, 300, 7):
                    r = sky.render(fixed(altitude, rising, t=t + s, weather=weather))
                    self.assertEqual(r["case"], r["cooler"])
                    self.assertEqual(r["case"], r["rear"])

    def test_sunrise_is_not_sunset_backwards(self):
        self.assertGreater(distance(stage(3, True), stage(3, False)), 0.1)

    def test_from_blue_to_gold_it_does_not_pass_through_bright_white(self):
        for rising in (True, False):
            for tenths in range(50, 140):
                rgb, brightness = sky.render(fixed(tenths / 10, rising))["case"]
                if max(rgb) - min(rgb) < 0.2:   # almost neutral: it must be dim there
                    self.assertLess(brightness, 0.6)

    def test_at_2_8_degrees_it_is_golden_hour_even_with_clouds(self):
        """A real sky at 2.8° was gold, and an earlier table gave red."""
        t = daytime()
        for coverage in (0.0, 0.6, 1.0):
            for s in range(0, 600, 5):
                rgb = sky.render(fixed(2.8, t=t + s, weather=overcast(t, coverage)))["cooler"][0]
                self.assertGreater(rgb[1] / rgb[0], 0.58)   # under 0.5 it is orange
                self.assertLess(rgb[2], rgb[1])             # and not pink

    def test_on_the_horizon_the_sky_is_orange_and_clouds_pink(self):
        t = daytime()

        def tone(coverage):
            return sky.render(fixed(-0.2, t=t, weather=overcast(t, coverage)))["cooler"][0]
        clear, cloud = tone(0.0), tone(1.0)
        self.assertLess(clear[2], 0.2)
        self.assertGreater(cloud[2], 0.35)
        self.assertGreater(cloud[2], clear[2] + 0.15)
        self.assertGreater(cloud[1], cloud[2])

    def test_after_orange_comes_lilac_and_darker(self):
        gold, orange, lilac = stage(3), stage(0), stage(-2)
        self.assertGreater(gold[1], orange[1])
        self.assertGreater(lilac[2], lilac[1])
        table = sky.stages(SETTINGS["sky"]["sunset"])
        self.assertLess(twilight.sky_at(table, -2)[1], twilight.sky_at(table, 0.8)[1] * 0.75)

    def test_the_end_of_twilight_is_not_deep_purple(self):
        """At low brightness blue weighs a lot on these LEDs: bytes 20, 2, 9 look deep purple, unlike any real sky."""
        for rising in (True, False):
            for tenths in range(-70, -34):
                rgb = stage(tenths / 10, rising)
                self.assertLess(rgb[0] - rgb[1], 0.1, tenths)


class Lightning(unittest.TestCase):
    def _storm(self, altitude=45.0, kind="storm"):
        t = daytime()
        return fixed(altitude, True, t=t, weather={"time": t + 100000, "coverage": 1.0, "kind": kind})

    def test_only_with_a_thunderstorm(self):
        self.assertEqual(sky.strikes(self._storm(kind="rain")), ())
        self.assertGreater(len(sky.strikes(self._storm())), 10)

    def test_none_at_night(self):
        self.assertEqual(sky.strikes(self._storm(altitude=-20.0)), ())

    def test_a_flash_is_short(self):
        ctx = self._storm()
        start, origin, _ = sky.strikes(ctx)[0]
        ctx.weather["time"] = start
        self.assertGreater(scenes.flash("sky", dataclasses.replace(ctx, t=start + 0.001))[scenes.ZONES[origin]], 0.5)
        self.assertEqual(scenes.flash("sky", dataclasses.replace(ctx, t=start + 1.5)), {})

    def test_frames_speed_up_only_near_a_strike(self):
        ctx = self._storm()
        strikes = sorted(s[0] for s in sky.strikes(ctx))
        ctx.weather["time"] = strikes[0]
        self.assertEqual(scenes.frame_delay("sky", dataclasses.replace(ctx, t=strikes[0] - 1)), sky.LIGHTNING_FRAME_S)
        gap = max(zip(strikes, strikes[1:]), key=lambda p: p[1] - p[0])
        self.assertEqual(scenes.frame_delay("sky", dataclasses.replace(ctx, t=(gap[0] + gap[1]) / 2)), sky.FRAME_S)


class Demo(unittest.TestCase):
    def test_sunset_goes_from_day_to_night(self):
        d = {"kind": "sunset", "start": 1000.0, "duration": 100.0}
        first = demo.demo_context(scenes.Context(1000.0, SETTINGS, demo=d))
        last = demo.demo_context(scenes.Context(1100.0, SETTINGS, demo=d))
        self.assertGreater(first.fixed_sun[0], 12)
        self.assertLess(last.fixed_sun[0], -9)
        self.assertFalse(first.fixed_sun[1])
        self.assertEqual(scenes.render("demo", scenes.Context(1100.0, SETTINGS, demo=d))["cooler"][1], 0)

    def test_nightfall_puts_the_leds_out(self):
        d = {"kind": "nightfall", "start": 1000.0, "duration": 100.0}
        self.assertEqual(scenes.leds_on("demo", scenes.Context(1000.0, SETTINGS, demo=d)), 1.0)
        self.assertAlmostEqual(scenes.leds_on("demo", scenes.Context(1050.0, SETTINGS, demo=d)), 0.5)
        self.assertEqual(scenes.render("demo", scenes.Context(1100.0, SETTINGS, demo=d))["cooler"][1], 0)

    def test_storm_works_without_a_place(self):
        d = {"kind": "storm", "start": 1000.0, "duration": 100.0}
        r = scenes.render("demo", scenes.Context(1050.0, SETTINGS, demo=d))
        self.assertGreater(r["case"][1], 0)
        self.assertLessEqual(r["case"][1], 0.28 * 1.2)

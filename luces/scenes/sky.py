"""The real sky: the Sun's altitude picks the color, and observed weather adds clouds, rain and lightning."""
from ..color import hex_to_rgb
from ..physics import clouds, storm, twilight
from ..physics.basics import clamp, mix
from ..physics.noise import fractal_noise
from .base import ZONES, Scene, altitude, off, rising

FRAME_S = 0.5
SMOOTHING_S = 2.5
LIGHTNING_FRAME_S = 0.04   # only near a strike: smoothing would swallow it
LIFE_SEED, LIFE_BRIGHTNESS_SEED = 21, 22


def stages(table):
    return [twilight.Stage(s["altitude"], hex_to_rgb(s["color"]), s["brightness"], s.get("leds", 1.0)) for s in table]


def current_table(ctx):
    sky = ctx.settings["sky"]
    return stages(sky["sunrise"] if rising(ctx) else sky["sunset"])


def weather_now(ctx):
    w = ctx.weather
    if not w or ctx.t - w.get("time", 0) > ctx.settings["sky"]["weather"]["max_age_h"] * 3600:
        return None
    return w


def render(ctx):
    sky = ctx.settings["sky"]
    if ctx.place is None and ctx.fixed_sun is None:
        return off(ctx)
    sun = altitude(ctx)
    table = current_table(ctx)
    base, brightness = twilight.sky_at(table, sun)
    if brightness <= 0 or twilight.leds_at(table, sun) <= 0:
        return off(ctx)
    w, life = sky["weather"], sky["life"]
    observed = weather_now(ctx) or {}
    coverage = clamp(observed.get("coverage", 0.0))
    override = w.get(observed.get("kind") or "")
    daylight = clamp(sun / 10)
    day = clamp((sun - 8) / 4)   # the blue only moves by day: in the golden hour it would put the gold out
    sun_on_cloud = clouds.sun_seen_by_cloud(sun, observed.get("cloud_height_km") or w["cloud_height_km"])
    cloud_rgb = clouds.cloud_color(sun_on_cloud, clouds.CloudColors(*(hex_to_rgb(w[k]) for k in clouds.CloudColors._fields)))
    cloud_share = w["cloud_mix"] * (w["clouds_at_sunset"] + (1 - w["clouds_at_sunset"]) * daylight) * clamp((sun_on_cloud + 6) / 3)
    result = {}
    for position, zone in enumerate(ZONES):
        t = ctx.t - position * w["zone_delay_s"] * day   # by day clouds cross the case; sunrise and sunset go in unison
        rgb = mix(base, hex_to_rgb(life["tone"]), life["mix"] * day * (0.5 + 0.5 * fractal_noise(t, life["period_s"], LIFE_SEED)))
        cloud = clouds.cloud_overhead(t, coverage, w["pass_s"], w["edge"], w["thin"])
        rgb = mix(rgb, cloud_rgb, cloud_share * cloud)
        value = brightness * (1 - (1 - w["overcast_brightness"]) * cloud * daylight)
        if isinstance(override, dict):
            rgb = mix(rgb, hex_to_rgb(override["color"]), 0.85)
            value = min(value, override["brightness"] / 100)
        result[zone] = (rgb, clamp(value * (1 + life["brightness"] * fractal_noise(t, life["period_s"], LIFE_BRIGHTNESS_SEED))))
    return result


def strikes(ctx):
    """The strikes near this instant. Only with a thunderstorm and with the sky on."""
    w = weather_now(ctx)
    if not w or w.get("kind") != "storm" or altitude(ctx) is None:
        return ()
    if altitude(ctx) <= ctx.settings["sky"]["sunset"][0]["altitude"]:
        return ()
    rate = round(ctx.settings["sky"]["lightning"]["per_hour"] * w.get("strike_rate", 1), 3)
    return storm.strikes_near(ctx.t, rate, len(ZONES))


def flash(ctx):
    lit = storm.flash_at(ctx.t, strikes(ctx), ctx.settings["sky"]["lightning"]["fade_s"], len(ZONES))
    return {ZONES[i]: strength for i, strength in lit.items()}


def leds_on(ctx):
    sun = altitude(ctx)
    return 1.0 if sun is None else twilight.leds_at(current_table(ctx), sun)


def near_lightning(ctx):
    return any(-2.0 <= start - ctx.t <= 2.5 for start, _, _ in strikes(ctx))


SCENE = Scene(render, FRAME_S, SMOOTHING_S, flash=flash, leds_on=leds_on,
              frame_delay=lambda ctx: LIGHTNING_FRAME_S if near_lightning(ctx) else FRAME_S)

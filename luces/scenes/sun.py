"""The real Sun with the motion of a campfire: colors and events come from NOAA, and the rhythm from physics/fire.py."""
from ..color import gradient, hex_to_rgb
from ..physics import solar_activity
from ..physics.basics import clamp, mix
from ..physics.fire import Campfire, Embers, Gusts, Restlessness, Tongues
from .base import ZONES, Scene

SPOT_SEED, FLARE_SEED = 1, 2


def activity(ctx):
    """From 0 to 1, from the flux of the last published day."""
    a, s = ctx.settings["sun"], ctx.solar
    if not s or ctx.t - s.get("fetched", 0) > a["max_age_h"] * 3600:
        return a["activity_without_data"]
    return solar_activity.activity_from_flux(s.get("flux", 0), a["flux_quiet"], a["flux_active"])


def render(ctx):
    a = ctx.settings["sun"]
    s = ctx.solar or {}
    spots, flares = a["sunspots"], a["flares"]
    spot_rate = min(spots["max"], spots["base"] + spots["per_number"] * s.get("sunspots", 40))
    flare_rate = min(flares["max"], flares["base"] + flares["c"] * s.get("c", 0) + flares["m"] * s.get("m", 0) + flares["x"] * s.get("x", 0))
    amplitude = a["flame_min"] + (a["flame_max"] - a["flame_min"]) * activity(ctx)
    restlessness = Restlessness(a["restlessness_s"])(ctx.t)
    fire = Campfire(Embers(a["ember_s"]), Gusts(a["gust_s"]), Tongues(a["tongue_s"], a["tongue_fall_s"]))
    last_zone = len(ZONES) - 1
    spots_now = solar_activity.events_near(ctx.t, spot_rate, SPOT_SEED, spots["duration_s"] + solar_activity.SPOT_DELAY_S * last_zone)
    flares_now = solar_activity.events_near(ctx.t, flare_rate, FLARE_SEED,
                                            flares["rise_s"] + 9 * flares["fall_s"] + solar_activity.FLARE_DELAY_S * last_zone)
    result = {}
    for position, zone in enumerate(ZONES):
        spot = solar_activity.sunspot_at(ctx.t, position, spots_now, spots["duration_s"])
        flare = solar_activity.flare_at(ctx.t, position, flares_now, flares["rise_s"], flares["fall_s"])
        flame = fire.at(ctx.t, amplitude * restlessness * (1 - spot), position, position * a["travel_s"])
        rgb = gradient(a["palette"], flame.heat)
        value = (a["brightness"] / 100) * (0.62 + 0.76 * flame.heat)
        rgb = mix(rgb, hex_to_rgb(a["sunspot"]), spot)
        value *= 1 - spots["darkens"] * spot
        flare *= 0.55 + 0.45 * flame.size   # a burst does not fall smoothly: it rises and falls with each tongue
        rgb = mix(rgb, hex_to_rgb(a["flare"]), flare)
        value *= 1 + 0.5 * flare
        result[zone] = (rgb, clamp(value))
    return result


SCENE = Scene(render, frame_s=0.066, smoothing_s=0.04, follows_schedule=True)

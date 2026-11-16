"""Clouds: when they cover the sky, and what color the setting Sun paints them.

Theory, measurements and sources: docs/physics/clouds.md.
"""
import math
from typing import NamedTuple

from .basics import clamp, mix, smoothstep
from .noise import even_noise

SEED = 23
EARTH_RADIUS_KM = 6371.0
REFRACTION = 0.5           # degrees: how far refraction bends sunlight around the Earth
REFERENCE_KM = 6.0         # cloud height that the colors of CloudColors were measured for


class CloudColors(NamedTuple):
    white: tuple       # the Sun high
    golden: tuple      # golden hour
    pink: tuple        # the Sun on the horizon
    afterglow: tuple   # 2° below the horizon: the last sunlight on the cloud
    gray: tuple        # 3° below: the cloud is in the Earth's shadow


def cloud_overhead(t, coverage, pass_s=40.0, edge=0.12, thin=0.65):
    """From 0 to 1: how much cloud hides the sky now. The share of time with a cloud overhead equals `coverage`.
    A cloud is not even: it enters thin, thickens to the center and thins out again, and lets the sky show in between.
    So not even an overcast sky stays one fixed color."""
    if coverage <= 0:
        return 0.0
    inside = coverage - even_noise(t, pass_s, SEED)
    present = 1.0 if coverage >= 1 else smoothstep(inside / edge + 0.5)
    return present * (thin + (1 - thin) * clamp(inside / coverage))


def earth_shadow_depth(height_km):
    """How many degrees below the horizon the Sun can be and still reach a cloud at that height, with refraction."""
    return math.degrees(math.acos(EARTH_RADIUS_KM / (EARTH_RADIUS_KM + height_km))) + REFRACTION


def sun_seen_by_cloud(sun_altitude, height_km):
    """The Sun's altitude as lived by a reference cloud: a higher cloud stays lit for longer."""
    return sun_altitude + earth_shadow_depth(height_km) - earth_shadow_depth(REFERENCE_KM)


def cloud_color(sun_altitude, colors):
    """White by day, golden in the golden hour, pink with the Sun on the horizon and gray in the Earth's shadow.
    It is the blend of two lights: the Sun's, redder and redder, and the sky's, which wins when the Sun stops reaching it."""
    if sun_altitude >= 3:
        return mix(colors.golden, colors.white, clamp((sun_altitude - 7) / 5))
    if sun_altitude >= 0:
        return mix(colors.pink, colors.golden, sun_altitude / 3)
    if sun_altitude >= -2:
        return mix(colors.afterglow, colors.pink, (sun_altitude + 2) / 2)
    return mix(colors.gray, colors.afterglow, clamp(sun_altitude + 3))

"""The color of the sky as a function of the Sun's altitude.

A scene gives a table of stages, and this module reads it at any altitude. Because the table is keyed by altitude and not
by time, each stage lasts what it really lasts: the clock of the day comes from sun_position.py.
Theory, measurements and sources: docs/physics/twilight.md.
"""
from dataclasses import dataclass

from .basics import mix


@dataclass(frozen=True)
class Stage:
    altitude: float           # degrees above the horizon
    rgb: tuple                # from 0 to 1
    brightness: float         # from 0 to 100
    leds: float = 1.0         # the share of LEDs that stay on, from 0 to 1


def _between(stages, altitude):
    """The two stages around an altitude, and how far along it is."""
    if altitude <= stages[0].altitude:
        return stages[0], stages[0], 0.0
    for low, high in zip(stages, stages[1:]):
        if altitude <= high.altitude:
            return low, high, (altitude - low.altitude) / (high.altitude - low.altitude)
    return stages[-1], stages[-1], 0.0


def sky_at(stages, altitude):
    """(rgb, brightness from 0 to 1) at that altitude, blending the two nearest stages."""
    low, high, x = _between(stages, altitude)
    return mix(low.rgb, high.rgb, x), (low.brightness + (high.brightness - low.brightness) * x) / 100


def leds_at(stages, altitude):
    """From 0 to 1: the share of LEDs on. At nightfall they go out one by one, without changing the color."""
    low, high, x = _between(stages, altitude)
    return low.leds + (high.leds - low.leds) * x

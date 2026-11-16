"""What every scene shares. A scene says, for an instant, the color and brightness of each zone.

Scenes keep no state: the same instant always gives the same result, which lets a whole day be simulated without
hardware. Smoothing between frames is done by the service.
"""
from dataclasses import dataclass
from typing import Callable

from ..physics.sun_position import HORIZON, last_sunset, sun_altitude

ZONES = ("case", "cooler", "rear")   # from front to back. With no separate rear fan, that zone is not painted
OFF = ((0.0, 0.0, 0.0), 0.0)


@dataclass
class Context:
    t: float
    settings: dict
    place: dict | None = None
    weather: dict | None = None
    solar: dict | None = None
    started_at: float = 0.0
    color: str | None = None
    forced_until: float | None = None
    demo: dict | None = None
    fixed_sun: tuple | None = None   # (altitude, rising), to show a stage without waiting for it


@dataclass(frozen=True)
class Scene:
    render: Callable             # context -> {zone: (rgb, brightness)}
    frame_s: float               # seconds between frames
    smoothing_s: float           # time constant of the fade towards each frame
    follows_schedule: bool = False
    flash: Callable | None = None         # context -> {zone: strength}, drawn above the smoothing
    leds_on: Callable | None = None       # context -> share of LEDs on
    frame_delay: Callable | None = None   # context -> seconds, if it changes during the scene


def altitude(ctx):
    if ctx.fixed_sun:
        return ctx.fixed_sun[0]
    return sun_altitude(ctx.t, ctx.place["lat"], ctx.place["lon"]) if ctx.place else None


def rising(ctx):
    if ctx.fixed_sun:
        return ctx.fixed_sun[1]
    return sun_altitude(ctx.t + 300, ctx.place["lat"], ctx.place["lon"]) > altitude(ctx)


def after_hours(ctx):
    """From some hours after the real sunset to the real sunrise: it shifts by itself with the seasons."""
    if ctx.place is None or altitude(ctx) >= HORIZON or (ctx.forced_until is not None and ctx.t < ctx.forced_until):
        return False
    sunset = last_sunset(ctx.t, ctx.place["lat"], ctx.place["lon"])
    return sunset is None or ctx.t - sunset >= ctx.settings["schedule"]["after_sunset_h"] * 3600


def off(ctx):
    return {zone: OFF for zone in ZONES}

"""A stage of the sky or a kind of weather, without waiting for it."""
import dataclasses

from ..physics.basics import clamp
from . import sky
from .base import Scene

FRAME_S = 0.25
SMOOTHING_S = 1.0
STAGES = ("sunrise", "sunset", "nightfall")
WEATHERS = {"clear": (0.0, None), "partly": (0.4, None), "cloudy": (0.7, None), "very-cloudy": (0.85, None),
            "overcast": (1.0, None), "rain": (1.0, "rain"), "storm": (1.0, "storm")}


def demo_context(ctx):
    d = ctx.demo or {}
    kind = d.get("kind", "clear")
    weather_name = d.get("weather") or (kind if kind in WEATHERS else "clear")
    coverage, weather_kind = WEATHERS.get(weather_name, (0.0, None))
    weather = {"time": ctx.t, "coverage": coverage, "kind": weather_kind, "strike_rate": 3}
    if kind in STAGES:
        x = clamp((ctx.t - d.get("start", ctx.t)) / max(d.get("duration", 60), 1))
        if kind == "nightfall":
            return dataclasses.replace(ctx, weather=weather, fixed_sun=(-4.5 - 4 * x, False))
        return dataclasses.replace(ctx, weather=weather, fixed_sun=(-9.5 + 23 * (x if kind == "sunrise" else 1 - x), kind == "sunrise"))
    return dataclasses.replace(ctx, weather=weather, fixed_sun=(45.0, True))


SCENE = Scene(lambda ctx: sky.render(demo_context(ctx)), FRAME_S, SMOOTHING_S,
              flash=lambda ctx: sky.flash(demo_context(ctx)),
              leds_on=lambda ctx: sky.leds_on(demo_context(ctx)),
              frame_delay=lambda ctx: sky.LIGHTNING_FRAME_S if sky.near_lightning(demo_context(ctx)) else FRAME_S)

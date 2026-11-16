"""A breathing guide: follow it with your breath, and it goes back to the previous scene by itself."""
from ..color import hex_to_rgb
from ..physics.breathing import breath_shape
from .base import ZONES, Scene


def render(ctx):
    a = ctx.settings["breathe"]
    x = breath_shape(ctx.t - ctx.started_at, a["inhale_s"], a["exhale_s"])
    brightness = (a["min_brightness"] + (a["max_brightness"] - a["min_brightness"]) * x) / 100
    return {zone: (hex_to_rgb(a["color"]), brightness) for zone in ZONES}


SCENE = Scene(render, frame_s=0.1, smoothing_s=0.15)

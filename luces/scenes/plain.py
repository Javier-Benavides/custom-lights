"""The two scenes with no motion: a fixed color, and off."""
from ..color import hex_to_rgb
from .base import ZONES, Scene, off


def render_color(ctx):
    rgb = hex_to_rgb(ctx.color or "#000000")
    return {zone: (rgb, 1.0) for zone in ZONES}


COLOR = Scene(render_color, frame_s=2.0, smoothing_s=1.0)
OFF_SCENE = Scene(off, frame_s=2.0, smoothing_s=1.0)

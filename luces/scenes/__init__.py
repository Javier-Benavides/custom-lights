"""All the scenes. To add one: write a module with a SCENE and register it here. See CONTRIBUTING.md."""
from . import breathe, demo, plain, relax, sky, sun
from .base import OFF, ZONES, Context, after_hours, altitude, off, rising   # noqa: F401

SCENES = {"sky": sky.SCENE, "sun": sun.SCENE, "relax": relax.SCENE, "breathe": breathe.SCENE,
          "color": plain.COLOR, "off": plain.OFF_SCENE, "demo": demo.SCENE}


def render(name, ctx):
    scene = SCENES[name]
    return off(ctx) if scene.follows_schedule and after_hours(ctx) else scene.render(ctx)


def flash(name, ctx):
    """From 0 to 1 per zone, only during a lightning strike."""
    scene = SCENES[name]
    return scene.flash(ctx) if scene.flash else {}


def leds_on(name, ctx):
    """The share of LEDs on now. Only the sky puts them out one by one."""
    scene = SCENES[name]
    return scene.leds_on(ctx) if scene.leds_on else 1.0


def frame_delay(name, ctx):
    """How long to wait for the next frame."""
    scene = SCENES[name]
    return scene.frame_delay(ctx) if scene.frame_delay else scene.frame_s

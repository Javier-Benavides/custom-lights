"""Green that comes and goes towards white, with a hidden pulse that invites slow breathing."""
from ..color import gradient, hex_to_rgb
from ..physics.basics import clamp, mix
from ..physics.breathing import breath_shape, breaths_taken
from ..physics.noise import even_noise, fractal_noise, swells
from .base import ZONES, Scene

PULSE_SEED, BRIGHTNESS_SEED, COLOR_SEED, STILLNESS_SEED = 31, 41, 44, 47


def render(ctx):
    a = ctx.settings["relax"]
    # Under the waves goes an almost invisible pulse, the same in every zone, that invites breathing at that rhythm
    # without asking for attention. It starts near a normal rhythm and slows down to the rhythm of the breathe scene.
    p, b = a["pulse"], ctx.settings["breathe"]
    length = b["inhale_s"] + b["exhale_s"]
    breaths = breaths_taken(ctx.t - ctx.started_at, p["start_s"], length, p["slowdown_min"] * 60) + 0.03 * fractal_noise(ctx.t, 60.0, PULSE_SEED)
    pulse = breath_shape((breaths % 1) * length, b["inhale_s"], b["exhale_s"])
    white = hex_to_rgb(a["palette"][-1])
    result = {}
    for position, zone in enumerate(ZONES):
        t = ctx.t - position * a["zone_delay_s"]
        wave = swells(t, a["cycle_s"], a["irregularity"], BRIGHTNESS_SEED)
        tone = swells(t, a["color_cycle_s"], a["irregularity"], COLOR_SEED)   # the color never stops, even if brightness settles
        stillness = 0.35 + 0.65 * even_noise(t, a["cycle_s"] * 6, STILLNESS_SEED)   # brightness sometimes nearly settles
        wave = 0.5 + (wave - 0.5) * stillness
        rgb = mix(gradient(a["palette"], 0.3 * wave + 0.7 * tone), white, p["tone"] * pulse)
        value = (a["min_brightness"] + (a["max_brightness"] - a["min_brightness"]) * wave) / 100
        result[zone] = (rgb, clamp(value * (1 + p["brightness"] * (2 * pulse - 1))))
    return result


SCENE = Scene(render, frame_s=0.2, smoothing_s=0.5, follows_schedule=True)

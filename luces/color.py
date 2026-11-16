"""From what the eye sees to the bytes each LED receives."""
from .physics.basics import clamp, mix

OFF_ORDER = (0, 4, 2, 6, 1, 5, 3, 7)   # the LED of each position, in the order they go out: each one far from the last


def hex_to_rgb(text):
    return tuple(int(text[i:i + 2], 16) / 255 for i in (1, 3, 5))


def rgb_to_hex(rgb):
    return "#" + "".join(f"{round(clamp(c) * 255):02X}" for c in rgb)


def gradient(palette, x):
    """A color along a list of hex colors, with x from 0 to 1."""
    if len(palette) == 1:
        return hex_to_rgb(palette[0])
    position = clamp(x) * (len(palette) - 1)
    i = min(int(position), len(palette) - 2)
    return mix(hex_to_rgb(palette[i]), hex_to_rgb(palette[i + 1]), position - i)


def to_linear(rgb, brightness, gamma):
    """An LED emits linear light and the eye does not: color and brightness become light before blending or smoothing."""
    factor = clamp(brightness) ** gamma
    return tuple((c ** gamma) * factor for c in rgb)


def led_share(i, on):
    """From 0 to 1: how much LED i shines if that share of the LEDs stays on. Each one goes out gradually."""
    n = len(OFF_ORDER)
    return clamp(on * n - (n - 1 - OFF_ORDER.index(i % n)))


def to_bytes(linear):
    """The largest channel leads and the others keep their proportion: at low brightness, rounding each one on its own
    changes the hue."""
    values = [clamp(c) * 255 for c in linear]
    largest = max(values)
    if largest <= 0:
        return (0, 0, 0)
    top = round(largest)
    return tuple(round(v / largest * top) for v in values)


def quantize(linear, leds, on=1.0):
    """Bytes for each LED, the same in all of them except those going out. Spreading the fraction across LEDs to gain
    resolution does not work here: the fans can be still, so each LED is seen on its own, and at low brightness
    (1, 0, 1), (0, 1, 1) and (0, 0, 1) look pink, green and blue."""
    return [to_bytes(tuple(c * led_share(i, on) for c in linear)) for i in range(leds)]

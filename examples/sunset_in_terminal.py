#!/usr/bin/env python3
"""A sunset in a few seconds, from the Sun's altitude, with the default stages. Clouds at 6 km are shown next to it.

    python3 examples/sunset_in_terminal.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from luces import settings                       # noqa: E402
from luces.color import hex_to_rgb               # noqa: E402
from luces.physics import clouds, twilight       # noqa: E402
from luces.scenes.sky import stages              # noqa: E402


def swatch(rgb, brightness=1.0):
    r, g, b = (round(255 * c * brightness) for c in rgb)
    return f"\033[48;2;{r};{g};{b}m          \033[0m"


def main():
    sky = settings.load(os.devnull)["sky"]
    table = stages(sky["sunset"])
    colors = clouds.CloudColors(*(hex_to_rgb(sky["weather"][k]) for k in clouds.CloudColors._fields))
    print("Sun altitude   sky          cloud")
    for tenths in range(140, -91, -10):
        altitude = tenths / 10
        rgb, brightness = twilight.sky_at(table, altitude)
        print(f"{altitude:8.1f}°     {swatch(rgb, brightness ** 0.5)}   {swatch(clouds.cloud_color(altitude, colors))}")


if __name__ == "__main__":
    main()

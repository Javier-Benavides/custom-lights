#!/usr/bin/env python3
"""A campfire in a terminal, with no LEDs and no settings: it uses only luces.physics.

    python3 examples/fire_in_terminal.py

Stop with Ctrl+C. Each bar is one of the three rhythms, and the block on the right is what they add up to.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from luces.physics.basics import mix          # noqa: E402
from luces.physics.fire import Campfire, Embers, Gusts, Tongues   # noqa: E402

DEEP_RED, ORANGE, YELLOW = (0.35, 0.05, 0.0), (1.0, 0.3, 0.0), (1.0, 0.8, 0.2)


def fire_color(heat):
    return mix(DEEP_RED, ORANGE, heat * 2) if heat < 0.5 else mix(ORANGE, YELLOW, heat * 2 - 1)


def bar(value, width=16):
    return "█" * round(min(value, 1.0) * width) + " " * (width - round(min(value, 1.0) * width))


def swatch(rgb, width=12):
    r, g, b = (round(255 * c) for c in rgb)
    return f"\033[48;2;{r};{g};{b}m{' ' * width}\033[0m"


def main():
    embers, gusts, tongues = Embers(), Gusts(), Tongues()
    fire = Campfire(embers, gusts, tongues)
    try:
        while True:
            t = time.time()
            flame = fire.at(t, strength=1.6)
            print(f"\rembers {bar(embers(t))} gusts {bar(gusts(t))} tongues {bar(tongues(t))} {swatch(fire_color(flame.heat))}", end="", flush=True)
            time.sleep(1 / 15)
    except KeyboardInterrupt:
        print()


if __name__ == "__main__":
    main()

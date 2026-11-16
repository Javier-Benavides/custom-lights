#!/usr/bin/env python3
"""Compares the sky model with colors measured in photos. To add a photo, add a line to PHOTO_POINTS.

Keep photos out of the repository, because they show a place. Only the Sun's altitude, the direction and the color go here,
and never the time. Theory and results: docs/physics/sky-color.md.
"""
import math
import os
import sys
import tomllib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from luces.physics.sky_model import Atmosphere, to_hex   # noqa: E402

# Sun altitude, view elevation, azimuth from the Sun, color measured in the photo
PHOTO_POINTS = [
    (2.83, 4, 0, "#E7BC63"), (2.83, 30, 100, "#313D54"),
    (-0.17, 8, 0, "#CDC9B0"), (-0.17, 15, 0, "#C4CEC9"), (-0.17, 25, 30, "#B3B9B9"),
    (-0.27, 4, 180, "#C99775"), (-0.27, 25, 170, "#7D8FA3"), (-0.27, 40, 170, "#677B8F"),
    (-1.01, 4, 170, "#D09D8D"), (-1.01, 20, 150, "#A2AABA"), (-1.01, 40, 150, "#818BA1"),
    (-1.03, 2, 0, "#EC9342"), (-1.03, 8, 20, "#CCC4B0"), (-1.03, 25, 80, "#787F86"),
    (-1.94, 4, 170, "#A27169"), (-1.94, 20, 170, "#666A7A"), (-1.94, 30, 170, "#737989"), (-1.94, 50, 170, "#646879"),
    (-1.91, 2, 0, "#FBC279"), (-1.91, 15, 30, "#BEBEBC"), (-1.91, 30, 80, "#A8ABAD"),
    (-2.73, 4, 170, "#897A83"), (-2.73, 30, 170, "#738298"), (-2.73, 40, 170, "#7C849B"), (-2.73, 60, 170, "#6A758C"),
    (-2.76, 2, 0, "#FED48B"), (-2.76, 10, 20, "#E4DED0"), (-2.76, 30, 80, "#B8BBB8"),
    (-3.89, 40, 170, "#425671"), (-3.89, 30, 170, "#3E4960"), (-3.89, 5, 170, "#525566"), (-3.92, 8, 10, "#D1C1A9"), (-3.92, 15, 30, "#C7BDB0"),
]
LED_GREEN, LED_BLUE = 0.8, 0.94    # estimated conversion from a photo to these LEDs, in linear light
CLOUD_DIRECT_SHARE = 0.02          # how much direct sunlight bounces towards the viewer; an estimate


def linear(hex_color, gamma=2.2):
    return [(int(hex_color[i:i + 2], 16) / 255) ** gamma for i in (1, 3, 5)]


def chromaticity(rgb):
    r, g, b = [max(x, 1e-6) for x in rgb]
    x, y, z = .4124 * r + .3576 * g + .1805 * b, .2126 * r + .7152 * g + .0722 * b, .0193 * r + .1192 * g + .9505 * b
    d = x + 15 * y + 3 * z
    return 4 * x / d, 9 * y / d


def distance(a, b):
    (u1, v1), (u2, v2) = chromaticity(a), chromaticity(b)
    return math.hypot(u1 - u2, v1 - v2)


def refraction(altitude):
    return 0.5 if altitude <= 0 else max(0.0, 0.5 * (1 - altitude / 6))


def modeled_spectrum(atmosphere, altitude, elevation, azimuth, fill):
    """Light scattered more than once comes from the whole sky, with the color of the zenith."""
    a = altitude + refraction(altitude)
    return [x + fill * y for x, y in zip(atmosphere.sky_spectrum(a, elevation, azimuth), atmosphere.sky_spectrum(a, 90, 0))]


def to_led(rgb):
    return to_hex((max(rgb[0], 0), max(rgb[1], 0) * LED_GREEN, max(rgb[2], 0) * LED_BLUE))


def table_color(stages, altitude):
    if altitude <= stages[0]["altitude"]:
        return stages[0]["color"]
    for low, high in zip(stages, stages[1:]):
        if altitude <= high["altitude"]:
            x = (altitude - low["altitude"]) / (high["altitude"] - low["altitude"])
            return to_hex([u + (v - u) * x for u, v in zip(linear(low["color"]), linear(high["color"]))])
    return stages[-1]["color"]


def best_fit():
    fits = []
    for aerosol in (0.03, 0.06, 0.1, 0.15, 0.2, 0.3, 0.4):
        atmosphere = Atmosphere(aerosol_depth=aerosol)
        for fill in (0.0, 0.15, 0.3, 0.5, 0.8, 1.2, 2.0):
            errors = [distance(atmosphere.to_rgb(modeled_spectrum(atmosphere, a, e, z, fill))[0], linear(h)) for a, e, z, h in PHOTO_POINTS]
            fits.append((sum(errors) / len(errors), max(errors), aerosol, fill))
    return sorted(fits)


def main():
    fits = best_fit()
    print("mean error, worst, aerosol, fill (0.01 in u'v' is barely visible side by side)")
    for fit in fits[:6]:
        print("  %.4f %.4f aerosol %.2f fill %.2f" % fit)
    print("  without fitting (aerosol .15, fill 0): %.4f" % next(f[0] for f in fits if f[2] == .15 and f[3] == 0))
    _, _, aerosol, fill = fits[0]
    atmosphere = Atmosphere(aerosol_depth=aerosol)
    print("\nChosen model against the photos")
    for a, e, z, h in PHOTO_POINTS:
        rgb = atmosphere.to_rgb(modeled_spectrum(atmosphere, a, e, z, fill))[0]
        print("  Sun %5.2f view %2d° azimuth %3d  photo %s  model %s  error %.3f" % (a, e, z, h, to_hex(rgb), distance(rgb, linear(h))))
    print("\nReference, a neutral gray against every photo: %.4f" % (sum(distance((1, 1, 1), linear(h)) for *_, h in PHOTO_POINTS) / len(PHOTO_POINTS)))

    with open(os.path.join(ROOT, "luces", "settings.toml"), "rb") as f:
        stages = tomllib.load(f)["sky"]["sunset"]
    print("\nColor per stage: the table (on LEDs), the model towards the Sun, and the average of the whole sky")
    views = [(e, z, math.cos(math.radians(e))) for e in (3, 8, 15, 25, 40, 60) for z in (0, 45, 90, 135, 180)]
    for altitude in (12, 10, 8, 6.5, 5, 3.5, 2.2, 1, 0, -0.8, -2, -3.5, -5, -6.5):
        horizon = atmosphere.to_rgb(modeled_spectrum(atmosphere, altitude, 4, 0, fill))[0]
        total = [0.0] * len(atmosphere.bands)
        for e, z, weight in views:
            total = [x + y * weight for x, y in zip(total, modeled_spectrum(atmosphere, altitude, e, z, fill))]
        whole = atmosphere.to_rgb(total)[0]
        print("  %5.1f   table %s   horizon %s (LED %s)   whole sky %s (LED %s)"
              % (altitude, table_color(stages, altitude), to_hex(horizon), to_led(horizon), to_hex(whole), to_led(whole)))

    print("\nCloud lit by the Sun, with fill from the sky: 3 km and 6 km")
    for altitude in (5, 2.8, 1, 0, -0.5, -1, -1.5, -2, -2.5, -3, -3.5):
        a = altitude + refraction(altitude)
        row = []
        for height in (3, 6):
            direct = atmosphere.direct_spectrum(a, height)
            light = [s * CLOUD_DIRECT_SHARE + z for s, z in zip(direct, atmosphere.sky_spectrum(a, 90, 0))]
            rgb = atmosphere.to_rgb(light)[0]
            row.append(f"{to_hex(rgb)} LED {to_led(rgb)}" + ("" if any(direct) else " (in shadow)"))
        print("  %5.1f   %s    %s" % (altitude, row[0].ljust(30), row[1]))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""The Sun's altitude through a day, with no network. Change the place and the date.

    python3 examples/sun_today.py 48.9 2.4
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from luces.physics.sun_position import HORIZON, crossing, sun_altitude   # noqa: E402


def main(argv):
    lat, lon = (float(x) for x in argv[:2]) if len(argv) >= 2 else (48.9, 2.4)
    start = int(time.time() // 86400) * 86400
    noon = max(range(start, start + 86400, 300), key=lambda t: sun_altitude(t, lat, lon))
    print(f"Highest: {sun_altitude(noon, lat, lon):.1f}° at {time.strftime('%H:%M', time.gmtime(noon))} UTC")
    for name, begin, end in (("rises", noon - 43200, noon), ("sets", noon, noon + 43200)):
        moment = crossing(begin, end, HORIZON, lat, lon)
        print(f"The Sun {name} at {time.strftime('%H:%M', time.gmtime(moment))} UTC" if moment else f"The Sun never {name} today")


if __name__ == "__main__":
    main(sys.argv[1:])

"""Downloads weather and solar activity. A timer runs it every hour.

If something fails it leaves the previous data: scenes know what to do with old data or none.
"""
import os
import sys
import time

from .. import paths, settings
from . import metar, satellite, solar_indices
from .fetch import FETCH_ERRORS, fetch_bytes, fetch_text

SOLAR_EVERY_S = 20 * 3600   # it is published once a day


def update(now=None, fetch=fetch_text, fetch_image=fetch_bytes):
    now = time.time() if now is None else now
    errors = 0
    place = settings.load_place()
    if place and place["stations"]:
        try:
            weather = metar.parse(fetch(metar.URL.format(",".join(place["stations"]))), now, place["stations"])
            if place["box"] and weather["temperature"] is not None:
                try:
                    satellite.add_satellite(weather, place["box"], now, fetch_image)
                except (*FETCH_ERRORS, settings.InvalidSettings) as e:
                    print(f"satellite: {e}", file=sys.stderr)   # the airport's report stays
            settings.write_json(paths.data("weather.json"), weather)
        except FETCH_ERRORS as e:
            print(f"weather: {e}", file=sys.stderr)
            errors += 1
    solar = settings.read_json(paths.data("solar.json"))
    if not solar or now - solar.get("fetched", 0) > SOLAR_EVERY_S:
        try:
            settings.write_json(paths.data("solar.json"), solar_indices.parse(fetch(solar_indices.URL), now))
        except FETCH_ERRORS as e:
            print(f"sun: {e}", file=sys.stderr)
            errors += 1
    return errors


def main():
    os.umask(0o022)
    update()
    return 0   # a failed source is not a service error: scenes go on without it

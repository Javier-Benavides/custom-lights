"""NOAA's daily solar indices: radio flux, sunspot number and flares of the last days."""
import re

from .fetch import InvalidData

URL = "https://services.swpc.noaa.gov/text/daily-solar-indices.txt"
ROW = re.compile(r"\d{4}\s+\d{1,2}\s+\d{1,2}\s")


def parse(text, now):
    """The last row with a valid flux. -999 means no data."""
    for line in reversed(text.splitlines()):
        if not ROW.match(line):
            continue
        p = line.split()
        if len(p) < 12:
            continue
        try:
            flux, sunspots = int(p[3]), int(p[4])
            area, c, m, x = int(p[5]), int(p[9]), int(p[10]), int(p[11])
        except ValueError:
            continue
        if flux < 0:
            continue
        return {"date": f"{p[0]}-{int(p[1]):02}-{int(p[2]):02}", "fetched": now, "flux": flux,
                "sunspots": max(0, sunspots), "area": max(0, area), "c": max(0, c), "m": max(0, m), "x": max(0, x)}
    raise InvalidData("no valid rows of solar activity")

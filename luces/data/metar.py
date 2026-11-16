"""METAR: what an airport weather station observed, in the hour it was observed. Never a forecast."""
import calendar
import re
import time

from .fetch import InvalidData

URL = "https://aviationweather.gov/api/data/metar?ids={}&format=raw"
COVERAGE = {"FEW": 0.2, "SCT": 0.45, "BKN": 0.75, "OVC": 1.0, "VV": 1.0}
CLEAR = {"CAVOK", "SKC", "CLR", "NSC", "NCD"}
FORECAST = {"NOSIG", "TEMPO", "BECMG", "RMK"}   # from here on the METAR talks about the future, which is not used
PHENOMENON = re.compile(r"[+-]?(?:MI|PR|BC|DR|BL|SH|TS|FZ)?(?:DZ|RA|SN|SG|IC|PL|GR|GS|UP|BR|FG|FU|VA|DU|SA|HZ|PO|SQ|FC|SS|DS)*")
CLOUD = re.compile(r"(FEW|SCT|BKN|OVC|VV)(\d{3}|///)(CB|TCU|///)?")
TIME = re.compile(r"(\d{2})(\d{2})(\d{2})Z")
TEMPERATURE = re.compile(r"(M?)(\d{2})/(?:M?\d{2})?")
PRIORITY = ("storm", "snow", "rain", "fog", "haze")
FRESH_S = 2 * 3600    # with older data, go to the next station
HIGH_CLOUD = 120      # from 12,000 feet clouds are thin: a BKN170 lets the blue show
HIGH_CLOUD_WEIGHT = 0.6
HUNDRED_FEET_KM = 0.03048


def _kind(phenomenon):
    if "TS" in phenomenon:
        return "storm"
    if any(x in phenomenon for x in ("SN", "SG", "PL", "GR", "GS", "IC")):
        return "snow"
    if "RA" in phenomenon or "DZ" in phenomenon:
        return "rain"
    if "FG" in phenomenon or "BR" in phenomenon:
        return "fog"
    if any(x in phenomenon for x in ("HZ", "FU", "DU", "SA")):
        return "haze"
    return None


def _observed_at(day, hour, minute, now):
    """A METAR gives day, hour and minute in UTC. Month and year come from today, taking care at month changes."""
    today = time.gmtime(now)
    year, month = today.tm_year, today.tm_mon
    if day > today.tm_mday + 1:
        month -= 1
        if month == 0:
            year, month = year - 1, 12
    try:
        return calendar.timegm((year, month, day, hour, minute, 0))
    except ValueError as e:
        raise InvalidData(f"impossible METAR time: {day} {hour}:{minute}") from e


def parse(text, now, stations=()):
    """What was observed. One line per station: the first of the list with fresh data wins, and if none has it, the
    newest. Some aerodromes do not report at night."""
    lines = [x for x in text.strip().splitlines() if x.strip()]
    if not lines:
        raise InvalidData("empty METAR")
    parsed, error = [], None
    for line in lines:
        try:
            parsed.append(_parse_line(line, now))
        except InvalidData as e:
            error = e
    if not parsed:
        raise error
    for station in stations:
        for d in parsed:
            if d["station"] == station and now - d["time"] <= FRESH_S:
                return d
    return max(parsed, key=lambda d: d["time"])


def _parse_line(line, now):
    """Ignores what comes after NOSIG, TEMPO, BECMG or RMK: that is a forecast."""
    tokens = line.rstrip("= ").split()
    first = next((i for i, f in enumerate(tokens) if TIME.fullmatch(f)), None)
    if first is None:
        raise InvalidData("METAR with no time")
    day, hour, minute = (int(x) for x in TIME.fullmatch(tokens[first]).groups())
    coverage, kinds, sky_seen, temperature, cloud_height = 0.0, set(), False, None, None
    for token in tokens[first + 1:]:
        if token in FORECAST:
            break
        cloud = CLOUD.fullmatch(token)
        if cloud:
            weight = HIGH_CLOUD_WEIGHT if cloud[2].isdigit() and int(cloud[2]) >= HIGH_CLOUD else 1.0
            if COVERAGE[cloud[1]] * weight > coverage and cloud[2].isdigit():
                cloud_height = round(int(cloud[2]) * HUNDRED_FEET_KM, 2)
            coverage, sky_seen = max(coverage, COVERAGE[cloud[1]] * weight), True
        elif token in CLEAR:
            sky_seen = True
        elif TEMPERATURE.fullmatch(token):
            sign, degrees = TEMPERATURE.fullmatch(token).groups()[:2]
            temperature = -int(degrees) if sign else int(degrees)
        elif len(token) >= 2 and PHENOMENON.fullmatch(token) and _kind(token):
            kinds.add(_kind(token))
    if not sky_seen:
        raise InvalidData("METAR with no cloud data")
    return {"time": _observed_at(day, hour, minute, now), "fetched": now, "coverage": coverage, "cloud_height_km": cloud_height,
            "kind": next((k for k in PRIORITY if k in kinds), None),
            "station": tokens[first - 1] if first else "", "temperature": temperature, "raw": line[:200]}

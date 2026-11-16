"""Reads and validates settings.toml and place.toml. An error says which line to fix."""
import json
import os
import re
import tempfile
import tomllib

from . import paths

HEX = re.compile(r"#[0-9A-Fa-f]{6}")
ICAO = re.compile(r"[A-Z0-9]{4}")
SCENES = ("sky", "sun", "relax", "breathe", "color", "off")
ZONE_NAMES = ("case", "cooler", "rear")
MIN_TONGUE_S = 0.45   # never more than 3 tongues a second: the limit for flickering light, see docs/decisions.md


class InvalidSettings(ValueError):
    pass


def _merge(base, extra):
    merged = dict(base)
    for key, value in extra.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _read_toml(path):
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        raise InvalidSettings(f"{path}: {e}") from e


def load(path=None):
    """The default settings with the user's on top. Raises InvalidSettings if something is wrong."""
    settings = _read_toml(paths.DEFAULT_SETTINGS)
    path = paths.control("settings.toml") if path is None else path
    if os.path.exists(path):
        settings = _merge(settings, _read_toml(path))
    validate(settings)
    return settings


class _Checker:
    def __init__(self, settings):
        self.settings = settings
        self.errors = []

    def value(self, key):
        current = self.settings
        for part in key.split("."):
            if not isinstance(current, dict) or part not in current:
                self.errors.append(f"{key} is missing")
                return None
            current = current[part]
        return current

    def number(self, key, low, high):
        v = self.value(key)
        if v is not None and (isinstance(v, bool) or not isinstance(v, (int, float)) or not low <= v <= high):
            self.errors.append(f"{key} must be a number between {low} and {high}")

    def color(self, key):
        v = self.value(key)
        if v is not None and not (isinstance(v, str) and HEX.fullmatch(v)):
            self.errors.append(f"{key} must be a #RRGGBB color")

    def palette(self, key):
        v = self.value(key)
        if v is not None and not (isinstance(v, list) and v and all(isinstance(c, str) and HEX.fullmatch(c) for c in v)):
            self.errors.append(f"{key} must be a list of #RRGGBB colors")


def _check_general(c):
    if c.value("general.initial_scene") not in SCENES:
        c.errors.append("general.initial_scene is not a known scene")
    c.number("general.max_brightness", 1, 100)
    c.number("general.gamma", 1, 3)
    c.number("schedule.after_sunset_h", 0, 12)
    c.number("schedule.on_choose_h", 0, 12)


def _check_zones(c):
    zones = c.settings.get("zones") if isinstance(c.settings.get("zones"), dict) else {}
    for zone in ("case", "cooler", *(["rear"] if "rear" in zones else [])):
        c.number(f"zones.{zone}.header", 1, 3)
        c.number(f"zones.{zone}.leds", 1, 256)
    if set(zones) - set(ZONE_NAMES):
        c.errors.append("zones only accepts case, cooler and rear")
    if zones and all(isinstance(z, dict) for z in zones.values()):
        headers = [z.get("header") for z in zones.values()]
        if len(set(headers)) != len(headers):
            c.errors.append("two zones cannot use the same header")


def _check_stages(c, table):
    stages = c.value(f"sky.{table}")
    if not isinstance(stages, list) or len(stages) < 2:
        c.errors.append(f"sky.{table} needs at least 2 stages")
        return
    altitudes = [s.get("altitude") for s in stages]
    if any(not isinstance(x, (int, float)) for x in altitudes) or altitudes != sorted(altitudes):
        c.errors.append(f"sky.{table} must be sorted by altitude")
    for i, s in enumerate(stages):
        if not HEX.fullmatch(str(s.get("color", ""))):
            c.errors.append(f"sky.{table}[{i}].color must be #RRGGBB")
        if not isinstance(s.get("brightness"), (int, float)) or not 0 <= s["brightness"] <= 100:
            c.errors.append(f"sky.{table}[{i}].brightness must be from 0 to 100")
        if "leds" in s and (not isinstance(s["leds"], (int, float)) or not 0 <= s["leds"] <= 1):
            c.errors.append(f"sky.{table}[{i}].leds must be from 0 to 1")


def _check_sky(c):
    _check_stages(c, "sunrise")
    _check_stages(c, "sunset")
    c.number("sky.weather.max_age_h", 0.1, 48)
    for name in ("white", "golden", "pink", "afterglow", "gray"):
        c.color(f"sky.weather.{name}")
    c.number("sky.weather.cloud_mix", 0, 1)
    c.number("sky.weather.clouds_at_sunset", 0, 1)
    c.number("sky.weather.cloud_height_km", 0.1, 15)
    c.number("sky.weather.overcast_brightness", 0, 1)
    c.number("sky.weather.pass_s", 10, 3600)
    c.number("sky.weather.edge", 0.05, 1)
    c.number("sky.weather.thin", 0, 1)
    c.number("sky.weather.zone_delay_s", 0, 600)
    for kind in ("rain", "storm", "snow", "fog", "haze"):
        c.color(f"sky.weather.{kind}.color")
        c.number(f"sky.weather.{kind}.brightness", 0, 100)
    c.color("sky.life.tone")
    c.number("sky.life.mix", 0, 1)
    c.number("sky.life.brightness", 0, 0.5)
    c.number("sky.life.period_s", 5, 3600)
    c.color("sky.lightning.color")
    c.number("sky.lightning.brightness", 1, 100)
    c.number("sky.lightning.per_hour", 0, 600)
    c.number("sky.lightning.fade_s", 0.02, 1)
    c.number("sky.satellite.contrast", 1, 100)
    c.number("sky.satellite.margin_k", 0, 30)


def _check_sun(c):
    c.palette("sun.palette")
    c.color("sun.sunspot")
    c.color("sun.flare")
    c.number("sun.brightness", 1, 100)
    c.number("sun.flame_min", 0, 3)
    c.number("sun.flame_max", 0, 3)
    c.number("sun.tongue_s", MIN_TONGUE_S, 10)
    c.number("sun.tongue_fall_s", 0.05, 5)
    c.number("sun.gust_s", 1, 120)
    c.number("sun.ember_s", 5, 600)
    c.number("sun.restlessness_s", 10, 3600)
    c.number("sun.travel_s", 0, 5)
    c.number("sun.flux_quiet", 0, 400)
    c.number("sun.flux_active", 1, 500)
    sun = c.settings.get("sun")
    if isinstance(sun, dict) and sun.get("flux_active", 1) <= sun.get("flux_quiet", 0):
        c.errors.append("sun.flux_active must be greater than sun.flux_quiet")
    c.number("sun.activity_without_data", 0, 1)
    c.number("sun.max_age_h", 1, 720)
    c.number("sun.sunspots.base", 0, 60)
    c.number("sun.sunspots.per_number", 0, 1)
    c.number("sun.sunspots.max", 0, 60)
    c.number("sun.sunspots.duration_s", 5, 600)
    c.number("sun.sunspots.darkens", 0, 1)
    for key in ("base", "c", "m", "x", "max"):
        c.number(f"sun.flares.{key}", 0, 60)
    c.number("sun.flares.rise_s", 1, 60)   # never a flash: rising takes at least 1 s
    c.number("sun.flares.fall_s", 1, 600)


def _check_relax(c):
    c.palette("relax.palette")
    c.number("relax.min_brightness", 0, 100)
    c.number("relax.max_brightness", 1, 100)
    c.number("relax.cycle_s", 10, 3600)
    c.number("relax.color_cycle_s", 10, 7200)
    c.number("relax.irregularity", 0, 1)
    c.number("relax.zone_delay_s", 0, 600)
    c.number("relax.pulse.start_s", 2, 30)
    c.number("relax.pulse.slowdown_min", 0, 60)
    c.number("relax.pulse.brightness", 0, 0.5)
    c.number("relax.pulse.tone", 0, 1)


def _check_breathe(c):
    c.color("breathe.color")
    c.number("breathe.min_brightness", 0, 100)
    c.number("breathe.max_brightness", 1, 100)
    c.number("breathe.inhale_s", 1, 30)
    c.number("breathe.exhale_s", 1, 30)
    c.number("breathe.minutes", 1, 120)


def validate(settings):
    c = _Checker(settings)
    for check in (_check_general, _check_zones, _check_sky, _check_sun, _check_relax, _check_breathe):
        check(c)
    if c.errors:
        raise InvalidSettings("; ".join(c.errors))


def load_place(path=None):
    """place.toml: lat, lon, stations in order of preference and, for the satellite, box: [south, west, north, east], an
    area with no tall mountains, because a mountain looks as cold as a cloud. It is private: see docs/data-sources.md.
    With no file, None."""
    path = paths.control("place.toml") if path is None else path
    if not os.path.exists(path):
        return None
    d = _read_toml(path)
    lat, lon, stations = d.get("lat"), d.get("lon"), d.get("stations", [])
    if not isinstance(lat, (int, float)) or not -90 <= lat <= 90:
        raise InvalidSettings("place.toml: lat must go from -90 to 90")
    if not isinstance(lon, (int, float)) or not -180 <= lon <= 180:
        raise InvalidSettings("place.toml: lon must go from -180 to 180")
    if not (isinstance(stations, list) and all(isinstance(s, str) and ICAO.fullmatch(s) for s in stations)):
        raise InvalidSettings("place.toml: stations must be a list of 4-letter ICAO codes")
    box = d.get("box")
    if box is not None and not (isinstance(box, list) and len(box) == 4 and all(isinstance(x, (int, float)) for x in box)
                                and -90 <= box[0] < box[2] <= 90 and -180 <= box[1] < box[3] <= 180):
        raise InvalidSettings("place.toml: box must be [south, west, north, east]")
    return {"lat": float(lat), "lon": float(lon), "stations": stations, "box": box}


def write_json(path, data):
    """Atomic write: a reader never sees half a file."""
    folder = os.path.dirname(path)
    fd, temporary = tempfile.mkstemp(dir=folder, prefix=".new-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        os.chmod(temporary, 0o644)
        os.replace(temporary, path)
    except BaseException:
        if os.path.exists(temporary):
            os.unlink(temporary)
        raise


def read_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else None
    except (OSError, ValueError):
        return None

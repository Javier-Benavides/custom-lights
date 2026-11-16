"""The `luces` command. It needs no sudo: it writes a small file that the service watches."""
import os
import shutil
import subprocess
import sys
import time

from . import chip_tools, desktop, paths, scenes
from . import settings as st
from .color import rgb_to_hex
from .physics import sun_position
from .scenes import demo as demo_scene

HELP = """luces: LED scenes driven by real physics

  luces next                  next mode: sky, sun, relax, off
  luces sky                   the real sky: Sun, clouds and rain
  luces sun                   the real Sun's colors and events, moving like a campfire
  luces relax                 soft green and white, with a pulse that invites slow breathing
  luces breathe [minutes]     breathing guide; then it goes back to what was on
  luces color '#FF5A14'       a fixed color
  luces off                   everything black
  luces brightness 40         overall brightness, from 0 to 100
  luces status                what is on and whether something fails
  luces today [YYYY-MM-DD]    at what time each stage of the sky happens that day
  luces settings              opens the settings to edit them
  luces shortcut [key]        creates the keyboard shortcut (Super+F12) and the dock icon
  luces shortcut remove       removes them

Without hardware:
  luces demo WHAT [minutes] [weather]   sunrise, sunset, nightfall or a weather, without waiting. Then it goes back
                              weather: clear, partly, cloudy, very-cloudy, overcast, rain or storm
  luces simulate SCENE [YYYY-MM-DD] [step_minutes] [weather]

Chip tests (with the service stopped):
  luces diagnose              reads what the chip says; changes no colors
  luces test ZONE COLOR       paints the color as the service would. ZONE: case, cooler, all, or a header: 1, 2 or 3
  luces test-chain ZONE       8 red LEDs, 8 green, 8 blue and 8 white
"""
CYCLE = ("sky", "sun", "relax", "off")
NAMES = {"sky": "Sky", "sun": "Sun", "relax": "Relax", "off": "Off"}
WEATHERS = demo_scene.WEATHERS
TIMED = ("breathe", "demo")   # they end by themselves and go back to the scene before


def _say(text):
    print(text)
    if not sys.stdout.isatty():
        desktop.notify(text)


def _mode():
    return st.read_json(paths.control("mode.json")) or {}


def _save(**changes):
    mode = _mode()
    mode.update(changes)
    st.write_json(paths.control("mode.json"), mode)


def _place():
    try:
        return st.load_place()
    except (OSError, st.InvalidSettings):
        return None


def _describe(name, settings, now):
    text = NAMES[name]
    ctx = scenes.Context(now, settings, _place())
    if name == "sky" and ctx.place and scenes.altitude(ctx) < settings["sky"]["sunset"][0]["altitude"]:
        return f"{text}: it is night, no lights until sunrise"
    if scenes.SCENES[name].follows_schedule and scenes.after_hours(ctx):
        return f"{text}: past the off time, staying on for {settings['schedule']['on_choose_h']:g} h"
    return text


def _choose(name, settings):
    now = time.time()
    forced = now + settings["schedule"]["on_choose_h"] * 3600 if scenes.SCENES[name].follows_schedule else None
    _save(scene=name, until=None, back_to=None, forced_until=forced)
    _say(_describe(name, settings, now))
    return 0


def _next(settings):
    mode = _mode()
    current = mode.get("scene") or settings["general"]["initial_scene"]
    if current in TIMED:
        current = mode.get("back_to") or "relax"
    i = CYCLE.index(current) if current in CYCLE else -1
    return _choose(CYCLE[(i + 1) % len(CYCLE)], settings)


def _breathe(args, settings):
    minutes = float(args[0]) if args else settings["breathe"]["minutes"]
    mode = _mode()
    previous = mode.get("scene")
    if previous in TIMED:
        previous = mode.get("back_to")
    _save(scene="breathe", until=time.time() + minutes * 60, back_to=previous or "relax")
    b = settings["breathe"]
    _say(f"Breathe for {minutes:g} min: inhale as it rises ({b['inhale_s']:g} s), exhale as it falls ({b['exhale_s']:g} s)")
    return 0


def _demo(args, settings):
    kind = args[0] if args else ""
    try:
        minutes = float(args[1]) if len(args) > 1 else (3.0 if kind in ("sunrise", "sunset") else 1.0)
    except ValueError:
        minutes = 0.0
    weather = args[2] if len(args) > 2 else None
    if (kind not in demo_scene.STAGES and kind not in WEATHERS) or not 0 < minutes <= 60 or (weather and weather not in WEATHERS):
        print("Usage: luces demo sunrise|sunset|nightfall|WEATHER [minutes] [weather]\nWeathers: " + ", ".join(WEATHERS))
        return 2
    mode = _mode()
    previous = mode.get("back_to") if mode.get("scene") in TIMED else mode.get("scene")
    now = time.time()
    _save(scene="demo", until=now + minutes * 60, back_to=previous or settings["general"]["initial_scene"],
          demo={"kind": kind, "weather": weather, "start": now, "duration": minutes * 60})
    _say(f"Demo of {kind} for {minutes:g} min. Then it goes back by itself")
    return 0


def _color(args):
    if not args or not st.HEX.fullmatch(args[0]):
        print("Usage: luces color '#RRGGBB'")
        return 2
    _save(scene="color", color=args[0], until=None, back_to=None)
    return 0


def _brightness(args):
    try:
        value = float(args[0])
    except (IndexError, ValueError):
        print("Usage: luces brightness 0-100")
        return 2
    if not 0 <= value <= 100:
        print("Brightness goes from 0 to 100")
        return 2
    _save(brightness=value)
    return 0


def _status():
    mode = _mode()
    print(f"Requested: {mode.get('scene', '(initial)')}, brightness {mode.get('brightness', 100):g} %")
    s = st.read_json(paths.run("status.json"))
    if not s:
        print("The service is not running.")
    else:
        age = time.time() - s.get("time", 0)
        print(f"Service: scene {s.get('scene')}, seen {age:.0f} s ago, chip firmware {s.get('firmware')}")
        for key in ("problem", "settings_error"):
            if s.get(key):
                print(f"Warning: {s[key]}")
    w = st.read_json(paths.data("weather.json"))
    if w:
        print(f"Weather, observed {(time.time() - w.get('time', 0)) / 60:.0f} min ago: {w.get('raw')}")
        if "satellite_coverage" in w:
            print(f"Clouds: {w['coverage'] * 100:.0f} %. Satellite {w['satellite_coverage'] * 100:.0f} %, at "
                  f"{time.strftime('%H:%M', time.localtime(w['satellite_time']))}; airport {w['airport_coverage'] * 100:.0f} %")
    sun = st.read_json(paths.data("solar.json"))
    if sun:
        print(f"Sun, {sun.get('date')}: flux {sun.get('flux')}, sunspots {sun.get('sunspots')}, "
              f"flares C{sun.get('c')} M{sun.get('m')} X{sun.get('x')}")
    return 0


def _settings():
    path = paths.control("settings.toml")
    if not os.path.exists(path):
        shutil.copy(paths.DEFAULT_SETTINGS, path)
    subprocess.call([os.environ.get("EDITOR", "nano"), path])
    try:
        st.load(path)
        print("Settings are valid.")
        return 0
    except st.InvalidSettings as e:
        print(f"Warning: {e}\nThe service keeps the last valid settings.")
        return 1


def _clock(t):
    return time.strftime("%H:%M", time.localtime(t))


def _today(args, settings):
    place = _place()
    if place is None:
        print("place.toml is missing from the control folder.")
        return 1
    lat, lon = place["lat"], place["lon"]
    start = time.mktime(time.strptime(args[0] if args else time.strftime("%Y-%m-%d"), "%Y-%m-%d"))
    noon = max(range(int(start), int(start) + 86400, 600), key=lambda t: sun_position.sun_altitude(t, lat, lon))
    rises = sun_position.crossing(noon - 43200, noon, sun_position.HORIZON, lat, lon)
    sets = sun_position.crossing(noon, noon + 43200, sun_position.HORIZON, lat, lon)
    if rises and sets:
        print(f"The Sun rises at {_clock(rises)} and sets at {_clock(sets)}.")
    for title, table, begin, end in (("Sunrise", "sunrise", noon - 43200, noon), ("Sunset", "sunset", noon, noon + 43200)):
        stages = [(sun_position.crossing(begin, end, s["altitude"], lat, lon), s) for s in settings["sky"][table]]
        stages = sorted((x for x in stages if x[0]), key=lambda x: x[0])
        if stages:
            print(f"\n{title}, {(stages[-1][0] - stages[0][0]) / 60:.0f} minutes:")
        for moment, s in stages:
            print(f"  {_clock(moment)}  Sun at {s['altitude']:5.1f}°  {s.get('stage', s['color'])}")
    return 0


def _swatch(rgb, brightness):
    r, g, b = (round(255 * c * brightness) for c in rgb)
    return f"\033[48;2;{r};{g};{b}m      \033[0m"


def _simulate(args, settings):
    if not args or args[0] not in scenes.SCENES:
        print("Usage: luces simulate SCENE [YYYY-MM-DD] [step_minutes] [weather]")
        return 2
    name = args[0]
    day = args[1] if len(args) > 1 else time.strftime("%Y-%m-%d")
    step = float(args[2]) if len(args) > 2 else 30.0
    weather = WEATHERS.get(args[3]) if len(args) > 3 else None
    place = _place()
    if name == "sky" and place is None:
        print("place.toml is missing from the control folder.")
        return 1
    start = time.mktime(time.strptime(day, "%Y-%m-%d"))
    for i in range(int(1440 / step)):
        t = start + i * step * 60
        ctx = scenes.Context(t, settings, place, started_at=start, solar=st.read_json(paths.data("solar.json")))
        if weather:
            ctx.weather = {"time": t, "coverage": weather[0], "kind": weather[1]}
        r = scenes.render(name, ctx)
        print(time.strftime("%H:%M", time.localtime(t)),
              *(f"{z} {_swatch(*r[z])} {rgb_to_hex(r[z][0])} {r[z][1] * 100:3.0f} %" for z in settings["zones"]), sep="  ")
    return 0


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(HELP)
        return 0
    command, args = argv[0], argv[1:]
    try:
        settings = st.load()
    except st.InvalidSettings as e:
        print(f"Warning: {e}")
        settings = st.load(os.devnull)
    if command in NAMES:
        return _choose(command, settings)
    with_settings = {"breathe": _breathe, "demo": _demo, "simulate": _simulate, "today": _today,
                     "test": chip_tools.test_color, "test-chain": chip_tools.test_chain}
    if command in with_settings:
        return with_settings[command](args, settings)
    if command == "next":
        return _next(settings)
    plain = {"status": _status, "settings": _settings, "diagnose": chip_tools.diagnose}
    if command in plain:
        return plain[command]()
    with_args = {"color": _color, "brightness": _brightness, "shortcut": desktop.shortcut}
    if command in with_args:
        return with_args[command](args)
    print(HELP)
    return 2

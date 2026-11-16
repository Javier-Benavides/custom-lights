# The physics

Every effect in luces starts from something real: a measured rhythm, a published formula or an observed data feed. Each page here explains one phenomenon, in the same order: what happens, the model, where it lives in the code, how to reuse it, sources, and limits.

| Phenomenon | Page | Code | Depends on |
|---|---|---|---|
| Where the Sun is | [sun-position.md](sun-position.md) | `luces/physics/sun_position.py` | Clock and place |
| Color of a clear sky, from first principles | [sky-color.md](sky-color.md) | `luces/physics/sky_model.py` | Sun altitude |
| Sunrise and sunset stages | [twilight.md](twilight.md) | `luces/physics/twilight.py` | Sun altitude |
| What aerosols, ozone and cloud height do to the colors | [atmosphere.md](atmosphere.md) | `luces/physics/sky_model.py` | Research, no scene uses it |
| How the evening changes through the year | [seasons.md](seasons.md) | `luces/physics/sun_position.py` | Latitude and date |
| Clouds and their color | [clouds.md](clouds.md) | `luces/physics/clouds.py` | Coverage, height, Sun altitude |
| Lightning | [storm.md](storm.md) | `luces/physics/storm.py` | Time |
| Campfire: embers, gusts, tongues | [fire.md](fire.md) | `luces/physics/fire.py` | Time |
| Sunspots and flares | [solar-activity.md](solar-activity.md) | `luces/physics/solar_activity.py` | NOAA indices |
| Slow breathing | [breathing.md](breathing.md) | `luces/physics/breathing.py` | Time |
| Noise with no memory | [noise.md](noise.md) | `luces/physics/noise.py` | Time |
| From physical color to LED bytes | [led-color.md](led-color.md) | `luces/color.py` | Research, not calibrated |

## How the pieces connect

```text
clock + place ──> sun_position ──> altitude ──┬─> twilight ──> sky color ──┐
                                              └─> clouds ──> cloud color ──┤
METAR + satellite ──> coverage, height, rain ──> clouds, storm ────────────┼─> scenes/sky.py
time ──> noise ──> fire ──> heat ──┐                                       │
NOAA indices ──> solar_activity ───┴──────────────────────> scenes/sun.py  │
time ──> noise, breathing ────────────────────────────────> scenes/relax.py
```

The physics modules never see settings, LEDs or files. They take numbers and give numbers, so any of them can be lifted out. A scene is the only place where they meet colors and zones.

## Using one piece elsewhere

```python
import time
from luces.physics.fire import Tongues
from luces.physics.sun_position import sun_altitude

flicker = Tongues(every_s=0.6)
print(flicker(time.time()))                      # a candle for a game, a shader, a sound
print(sun_altitude(time.time(), 48.9, 2.4))      # degrees above the horizon
```

See [`examples/`](../../examples) for complete programs.

## What the numbers are worth

Each page has a "Limits" section. Read it before trusting a value. Three kinds of number live in this code, and they are not equally solid:

- **Published:** formulas and measurements with a source, like the position of the Sun.
- **Measured here:** comparisons with photos or tests, on one evening or one set of LEDs.
- **Design:** values chosen by eye because they look right, like the length of a gust.

## Open questions

Good issues to work on, once a maintainer writes the spec:

1. **Cloud color by formula:** replace the five fixed colors with direct light plus sky light, see [clouds.md](clouds.md).
2. **Clear sky by formula:** the literal average of the sky is almost white, so it has to be defined which light the LEDs show.
3. **Air data:** which source to use for aerosol depth, see [atmosphere.md](atmosphere.md). A new host is a security decision.
4. **LED calibration:** how to measure the device layer, see [led-color.md](led-color.md).
5. **Local horizon:** a profile by azimuth for sunrise and sunset, see [seasons.md](seasons.md).
6. **A diary of evenings:** a way to record what was seen by Sun altitude, with no time or place.

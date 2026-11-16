# Storms and lightning

## What happens

- **A storm is dark.** Thick clouds absorb light, so a rainy sky is a dim bluish gray, and a thunderstorm is darker still.
- **A bolt flickers.** A lightning flash is usually made of several return strokes in the same channel, a fraction of a second apart.

## The model

Rain and storm are overrides in `[sky.weather]`: a color at 85 % and a brightness limit. Lightning only appears when a METAR reports a thunderstorm (`TS`).

Each strike is drawn per hour from a fixed seed, so any instant can be computed without history:

- 1 to 3 strokes, 0.12 to 0.3 s apart, never more than 3 in a second.
- Each stroke fades exponentially, with `fade_s` of 0.06 s.
- It is born in one zone and reaches the others weaker (55 % per zone) and 30 ms later.

Lightning is drawn after smoothing, because it lasts less than the smoothing does, and the service speeds up to 25 frames a second only near a strike.

## In the code

`luces/physics/storm.py`

| Function | Gives |
|---|---|
| `strikes_in_hour(hour, rate, zones)` | Every strike of an hour |
| `strikes_near(t, rate, zones)` | Those of this hour and the last |
| `flash_at(t, strikes, fade_s, zones)` | `{zone: strength}`, only for lit zones |

`luces/scenes/sky.py` decides when lightning is allowed: with a storm, and with the sky on. `luces demo storm 2` shows it.

## Use it elsewhere

```python
from luces.physics.storm import strikes_near, flash_at
strikes = strikes_near(t, rate=20)
lit = flash_at(t, strikes, fade_s=0.06, zones=1)
```

## Limits

- Stroke counts and spacing are design, inspired by how a flash behaves, not fitted to data.
- The rate is fixed by settings, not by real lightning data.
- Flashes are a known trigger for some people. The 3-a-second limit is part of the design, see [../decisions.md](../decisions.md).

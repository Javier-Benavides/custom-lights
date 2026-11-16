# Sunrise and sunset

How the light changes as the Sun crosses the horizon, and why the stages come from an angle and not a clock.

## What happens

Going down, from the Sun at +12° to night at -8°:

| Sun altitude | What the sky does | Stage in `settings.toml` |
|---|---|---|
| +12° | Day | Sky blue |
| +10° to +8° | The light drops | Slate blue and light brown, dim |
| +6.5° to +2° | Golden hour | Gold |
| +1° to -0.3° | Sun on the horizon | Orange |
| -1.2° | Just set | Soft salmon |
| -2° | The color fades upward | Pinkish lilac |
| -2.7° to -3.5° | The Earth's shadow rises | Bluish gray |
| -5° and below | Blue, then dark | Blue, with LEDs going out one by one until -8° |

Hours like "golden" and "blue" are photographers' conventions with no official definition. The Belt of Venus is measured: it appears with the Sun near -2°, loses its red between -3° and -6°, and disappears near -8°.

## The model

A table of stages keyed by altitude. Between two stages the color blends linearly. Because the key is the angle, the real length of each stage appears by itself: from sky blue to night takes about 100 minutes at mid latitudes, more in winter than near the equinoxes.

Sunrise and sunset have separate tables because they need not match. With mountains to the east, the sky lights up long before the Sun is seen, and the Sun appears some degrees above the true horizon.

Three lessons from tuning this against a real evening:

- **Blue and orange do not blend well.** At full brightness their mix passes through white, which a real sky never shows. So the table crosses dim, through slate blue and light brown.
- **Low brightness is not a dimmer color.** At low brightness blue weighs a lot on LEDs: bytes `20, 2, 9` looked deep purple while the real sky was grayish blue. That is why the table ends in blue with green above red.
- **At nightfall, turn LEDs off instead of dimming.** Below about 20 % brightness colors fall apart, so from -5° the color stays and the share of LEDs on goes from 1 to 0. `color.OFF_ORDER` jumps around the ring so the light stays even.

## In the code

`luces/physics/twilight.py`: `Stage`, `sky_at(stages, altitude)` and `leds_at(stages, altitude)`. The table itself is data, in `[[sky.sunset]]` and `[[sky.sunrise]]`.

`luces/scenes/sky.py` picks the table with `rising(ctx)`, and `luces demo sunset` runs a whole sunset in 3 minutes.

## Use it elsewhere

```python
from luces.physics.twilight import Stage, sky_at
table = [Stage(-6, (0.1, 0.1, 0.4), 20), Stage(0, (1.0, 0.4, 0.1), 70), Stage(12, (0.4, 0.7, 1.0), 60)]
rgb, brightness = sky_at(table, sun_altitude)
```

## Limits

- The altitudes were compared with one clear evening and one set of fans. The sunrise table has not been compared with a real sunrise.
- Colors are calibrated for one set of LEDs and must be retuned on others, see [../hardware.md](../hardware.md).
- All zones share one color: a real sky differs between east and west, and the Sun's side stays warm longer.

## Sources

- [Belt of Venus, measured](https://pubmed.ncbi.nlm.nih.gov/25967826)
- [Sky & Telescope: the Belt of Venus](https://skyandtelescope.org/astronomy-blogs/the-belt-of-venus/)
- [Golden and blue hours](https://photoephemeris.com/en/articles/magical-gold-and-blue-confusion-in-the-twilight-zone)

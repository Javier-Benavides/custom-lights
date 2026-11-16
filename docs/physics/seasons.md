# How the evening changes through the year

The Sun crosses the sky at a different angle in summer and in winter. That changes how long each color lasts. It does not change which color goes with each altitude: for the same air, the light at 5° crosses the same path in any season.

The scenes follow the Sun's altitude, never the clock, so the durations below happen by themselves. **No seasonal rule is needed for them.**

## The geometry

For latitude φ, solar declination δ and hour angle H:

```text
sin h = sin φ sin δ + cos φ cos δ cos H
dh/dt = -15° per hour × cos φ cos δ sin H / cos h
```

The Sun drops fastest when its path is steepest against the horizon. That happens at the equinoxes. At the solstices the path is more slanted, so the same degrees take longer.

## Minutes per stretch, at 35° of latitude

| Date | Noon altitude | 12° to 6.5° | 6.5° to 0.8° | 0.8° to -2° | -2° to -8° | Total |
|---|---|---|---|---|---|---|
| Equinox | 55° | 27.0 | 27.9 | 13.7 | 29.4 | 98 |
| Summer solstice | 78° | 29.0 | 31.0 | 15.7 | 35.1 | 111 |
| Winter solstice | 32° | 33.8 | 32.9 | 15.6 | 32.4 | 115 |

What it shows:

- **Equinoxes are the shortest,** not one season against the other: an evening lasts up to 17 % longer at either solstice.
- **The stretch above the horizon lasts longest in winter,** and the stretch after sunset lasts longest in summer.
- The difference grows with latitude. Near the poles, twilight can last hours or never end.

Run `luces today 2026-12-21` for any date at your own place.

## What the year does change

- **The direction of sunset.** At the horizon `cos A = sin δ / cos φ`, with A measured from the pole on your side of the sky. At 35° the sunset moves about 29° to each side of due west. So a different hill or building hides the Sun, and on the same day the Sun can vanish behind one at 1.7° while the sky goes on. The same applies at sunrise. A mountain range that hides the Sun up to 5° in one month may do it up to 8° in another.
- **The noon altitude.** It only matters above the twilight tables, where the sky color is fixed. In `sky_model.py` the zenith is clearly bluer with the Sun at 33° than at 80°, while the sky far from the Sun hardly changes. That effect is small next to the rest.
- **The air.** This is the one that changes the intensity of the colors, see [atmosphere.md](atmosphere.md). Humidity, dust, smoke and the height of the mixed layer change with the seasons in ways that depend on the place.

## Open work

- A horizon profile by azimuth in `place.toml`: the altitude of the local horizon in each direction. It would replace the fixed altitude in the sunrise table. Nothing reads one yet.
- A diary of real evenings, by Sun altitude, through a whole year. This is the only way to test any of this.

## Limits

- The table uses a mean declination, no refraction, and a generic latitude.
- It says how long the Sun takes to cross those altitudes, not what your eye will see.

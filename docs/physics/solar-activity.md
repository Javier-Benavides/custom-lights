# Solar activity

The `sun` scene shows what the real Sun did: a busy day looks different from a quiet one.

## What happens

- **Radio flux at 10.7 cm** is the standard daily measure of how active the Sun is, from about 70 when quiet to over 200.
- **Sunspots** are cooler, dark regions. Their number rises and falls with the 11-year cycle.
- **Flares** are sudden releases of energy, classed C, M and X. They rise fast and decay slowly, and small ones are far more common than big ones: their frequency falls with energy as a power law with a slope near 1.8.

## The model

| Data | Effect in the scene |
|---|---|
| Flux | From `flux_quiet` to `flux_active`: activity from 0 to 1, which sets the height of the flames |
| Sunspot number | Dark moments per hour: `base + per_number × sunspots`, up to `max` |
| C, M and X flares of the last day | Yellow bursts per hour: `base + c·C + m·M + x·X`, up to `max` |

Events are drawn per hour from a fixed seed. Each one is born in one zone and reaches the others weaker and later. A sunspot darkens the zone and puts its flames out, leaving the black part. A flare rises in 2 s and falls more slowly the stronger it is, and it rises and falls with each tongue of fire.

Time is accelerated: a real sunspot lasts days, and here it lasts 30 s.

## In the code

`luces/physics/solar_activity.py`

| Function | Gives |
|---|---|
| `activity_from_flux(flux, quiet, active)` | From 0 to 1 |
| `events_in_hour(hour, rate, seed, zones)` | `(start, zone, strength)`, with power law strengths |
| `events_near(t, rate, seed, lasting_s, zones)` | Only the events in progress |
| `sunspot_shape`, `flare_shape` | The shape of each event in time |
| `sunspot_at`, `flare_at` | How much reaches a zone now |

The data come from [`luces/data/solar_indices.py`](../data-sources.md).

## Use it elsewhere

```python
from luces.physics.solar_activity import events_near, flare_at
flares = events_near(t, rate=30, seed=2, lasting_s=120, zones=1)
burst = flare_at(t, 0, flares, rise_s=2, fall_s=8)
```

The power law generator fits any event with many small and few big ones.

## Limits

- It is a mood, not a measurement: the flares shown are not at the real times.
- With no recent data, it uses `activity_without_data`.

## Sources

- [NOAA daily solar indices](https://services.swpc.noaa.gov/text/daily-solar-indices.txt)
- [Lu and Hamilton, 1991: the power law of solar flares](https://adsabs.harvard.edu/pdf/1991ApJ...380L..89L)

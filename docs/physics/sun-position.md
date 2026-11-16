# Where the Sun is

Everything in the sky scene follows one number: the altitude of the Sun above the horizon. It comes from the clock and the place, with no network.

## What happens

The Sun's position depends on the Earth's tilt, its orbit and the time. Using the altitude instead of the clock is what makes colors follow the year by themselves: the golden hour comes when the Sun is low, whatever the time says. It also makes each stage last what it really lasts, because the Sun sets faster or slower depending on the season and the latitude.

## The model

NOAA's solar calculator, based on Meeus, *Astronomical Algorithms*:

1. From the date to Julian centuries since J2000.
2. Mean longitude and anomaly of the Sun, and the equation of center, give its apparent longitude.
3. The obliquity of the ecliptic gives the declination δ.
4. The equation of time corrects the clock to solar time, which gives the hour angle H.
5. Altitude: `sin(a) = sin(φ)·sin(δ) + cos(φ)·cos(δ)·cos(H)`, with φ the latitude.

Accuracy is about a minute between latitudes ±72°.

`HORIZON = -0.833°` is where the Sun is seen to rise and set: the disc's radius (0.27°) plus refraction (about 0.57°). The altitude here does not include refraction.

## In the code

`luces/physics/sun_position.py`

| Function | Gives |
|---|---|
| `sun_altitude(epoch, lat, lon)` | Degrees above the horizon |
| `crossing(start, end, altitude, lat, lon)` | When the Sun reaches an altitude, by bisection |
| `last_sunset(epoch, lat, lon)` | The last sunset, for "some hours after sunset" |

`luces today` uses `crossing` to print the time of each stage of the day.

## Use it elsewhere

```python
from luces.physics.sun_position import sun_altitude, crossing
altitude = sun_altitude(time.time(), 48.9, 2.4)
```

It needs only `math`, so the file can be copied alone.

## Limits

- No refraction in the altitude: near the horizon the real Sun looks about half a degree higher.
- The horizon is assumed flat. Mountains delay the sunrise you see, which the tables in `settings.toml` must account for by hand.
- Near the poles there may be no sunset: `last_sunset` returns `None`.

## Sources

- [NOAA solar calculation details](https://gml.noaa.gov/grad/solcalc/calcdetails.html)
- Jean Meeus, *Astronomical Algorithms*

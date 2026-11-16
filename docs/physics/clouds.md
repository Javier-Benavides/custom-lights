# Clouds

How much of the time a cloud covers the sky, and what color the setting Sun paints it.

## What happens

- **Coverage is time.** A fan cannot draw a cloud, so a cloud becomes a moment: with 70 % coverage, a cloud is overhead 70 % of the time, with gaps of sky between.
- **A cloud is not even.** It enters thin, thickens to the center and thins out. Even an overcast sky is not one fixed color.
- **Its color is a blend of two lights:** direct sunlight, redder and redder, and light from the sky, which wins when the Sun stops reaching it.
- **The Earth's shadow.** After sunset a cloud stays lit until the shadow reaches its height. A cloud at height h sees the Sun down to `acos(R/(R+h))` below the horizon, plus about 0.5° of refraction: about -2.3° at 3 km and -3° at 6 km.

| Sun as seen by a 6 km cloud | Cloud |
|---|---|
| Above +12° | White |
| +7° to +3° | Gold |
| 0° | Pink |
| -2° | Bright pink, the afterglow |
| -3° and below | Gray: it is in the shadow |

A cloud at another height lives the same stages earlier or later: `sun_seen_by_cloud` shifts the Sun by the difference in shadow depth.

## The model

`cloud_overhead` cuts evenly spread noise at the coverage, so the share of time is exact, with soft edges. Measured over six hours at 70 %: 69 % of the time with cloud, 48 gaps an hour, a typical gap of 16 s and a typical cloud of 30 s.

## In the code

`luces/physics/clouds.py`

| Function | Gives |
|---|---|
| `cloud_overhead(t, coverage, pass_s, edge, thin)` | From 0 to 1, how much cloud hides the sky now |
| `earth_shadow_depth(height_km)` | Degrees the Sun can be below the horizon and still reach it |
| `sun_seen_by_cloud(sun_altitude, height_km)` | The altitude a 6 km cloud would need to look like this one |
| `cloud_color(sun_altitude, colors)` | The color, from five `CloudColors` |

Coverage and height come from METAR and satellite, see [../data-sources.md](../data-sources.md).

## Use it elsewhere

```python
from luces.physics.clouds import cloud_overhead, earth_shadow_depth
dim = 1 - 0.4 * cloud_overhead(time.time(), coverage=0.7)   # dim any light as if clouds passed
```

## Toward a formula for the cloud color

The code today moves between five fixed colors. A trial replaced them with physics: **direct sunlight at the height of the cloud, plus the light of the sky,** both from `luces/physics/sky_model.py`, with equal weight. **No scene uses it yet.**

Against one real evening, with clouds reported at 2 km, as green/red and blue/red:

| Sun altitude | Formula | Seen | The code today |
|---|---|---|---|
| 1.67° | 0.51/0.13, gold | Gold | Already salmon |
| 0.92° | 0.43/0.08, orange | Orange | Salmon |
| 0.23° | 0.35/0.09, deep orange | First pink tones | Salmon |
| -0.26° | 0.36/0.20, orange and pink | Strong orange, some pink | Pink |
| -1.14° | 0.97/1.05, pale lilac | Pink and lilac | Pink |
| -2.27° | 1.16/1.46, blue gray | Dark gray | Blue gray |

- The formula gets the order right with no hand-made stages, and it adds the orange stage the code skips.
- It makes pink paler than the real one.
- The weight was picked by looking at this same evening, so the next evenings are the real test.
- Cloud height changes everything, see the table in [atmosphere.md](atmosphere.md). METAR reports the lowest layer at an airport.
- The code shifts the whole curve by cloud height. Below the horizon that is right, because a low cloud enters the Earth's shadow first. Above the horizon it made pink arrive too soon.
- Thin high clouds catch unfiltered light and low ones get it through the hazy lower air, which is why [Corfidi](https://www.spc.noaa.gov/publications/corfidi/sunset/) finds cirrus and altocumulus the most vivid. Ground color can also tint a low cloud from below, as [Gedzelman](https://atoptics.co.uk/blog/tilting-at-clouds-in-la-manch-cloud-colours-opod) modeled.

## Limits

- The color stages were checked on one evening: a model gave `#FFC89A` for a 6 km cloud where a photo gave `#FFC390`.
- One height per sky: real skies have layers.
- The time between clouds is design, not measured from a real sky.

## Sources

The geometry is plain trigonometry. The colors come from [sky-color.md](sky-color.md).

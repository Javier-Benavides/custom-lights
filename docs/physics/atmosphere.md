# What the air does to the colors

The Sun's altitude sets how much air the light crosses. The air decides what survives. That is why the same altitude can give a vivid evening one day and a pale one the next.

This page is research. **No scene uses aerosol data yet.**

## What happens

- **Path length:** the light crosses more air as the Sun drops. The Kasten and Young formula gives the relative air mass from the altitude γ, in degrees: `X = 1 / (sin γ + 0.50572 (γ + 6.07995)^-1.6364)`. It is 2 at 30°, 4.7 at 12°, 8.2 at 6.5°, 15 at 3°, 27 at 0.9° and about 38 at the horizon.
- **Molecules:** Rayleigh scattering removes blue first. Optical depth at sea level, with λ in micrometers: `τ = 0.008569 λ^-4 (1 + 0.0113 λ^-2 + 0.00013 λ^-4)`, about 0.1 at 550 nm (Hansen and Travis, 1974).
- **Aerosols:** particles close to the size of the wavelength scatter all colors, dim the light and wash the sky toward white. Their amount is the aerosol optical depth (AOD), and its color dependence is the Ångström exponent α: `τ(λ) = τ550 (λ / 550 nm)^-α`.
- **Ozone:** the Chappuis band absorbs orange and yellow. It keeps the sky blue after sunset, and matters little before.
- **Clouds:** they catch the light and show it. How they do it is in [clouds.md](clouds.md).
- **High layers:** some 15 minutes after sunset the lower air is in shadow and only the stratosphere is lit. Aerosols there, as after a large eruption, give purple afterglows.

## Clean air is what looks vivid

Popular belief says pollution makes better sunsets. The evidence says otherwise:

- Corfidi (NOAA, 2014) names clean air as the main ingredient of vivid twilights. Low-level haze turns them pale yellow or pink, and dims them.
- Saito, Iwabuchi and Hayasaka (2013) measured it: with more tropospheric aerosol, the twilight sky near the horizon gets darker and bluer. Reddish single scattering weakens, and bluish multiple scattering takes over.
- Zerefos and others (2014) went the other way: they estimated AOD from the red to green ratio of sunsets, in paintings and in a field test with sun photometers. Their conclusion is tentative, but it shows the color carries the information.
- Studies of twilight color disagree on details. Lee and Hernández-Andrés (2003) found that purple light needs scattering in both the troposphere and the stratosphere, and a 2011 study found aerosol extinction matters about as much as ozone.

## What the model says

`luces/physics/sky_model.py`, light on a cloud: direct sunlight at the height of the cloud plus the light of the sky. Each cell is green/red and blue/red in linear light. Base: AOD 0.15 at 550 nm, α 1.3, aerosol layer 1.5 km, ozone 300 DU, cloud at 2 km.

| Sun altitude | 1.67° | 0.92° | 0.23° | -0.26° | -1.14° |
|---|---|---|---|---|---|
| Base | 0.51/0.13 | 0.43/0.08 | 0.35/0.09 | 0.36/0.20 | 0.97/1.05 |
| Clean air, AOD 0.05 | 0.56/0.16 | 0.47/0.09 | 0.38/0.05 | 0.31/0.06 | 0.40/0.36 |
| Hazy air, AOD 0.40 | 0.43/0.10 | 0.39/0.14 | 0.51/0.35 | 0.74/0.63 | 0.92/0.95 |
| Ozone 250 DU | 0.51/0.12 | 0.42/0.08 | 0.35/0.09 | 0.36/0.19 | 0.95/0.94 |
| Ozone 350 DU | 0.52/0.14 | 0.43/0.09 | 0.35/0.10 | 0.36/0.21 | 0.99/1.16 |
| Aerosol layer 0.8 km | 0.55/0.15 | 0.47/0.09 | 0.37/0.05 | 0.30/0.07 | 1.08/1.21 |
| Aerosol layer 3 km | 0.49/0.13 | 0.42/0.11 | 0.39/0.17 | 0.45/0.30 | 0.80/0.75 |
| α 1.0 | 0.53/0.15 | 0.45/0.10 | 0.38/0.10 | 0.39/0.22 | 0.99/1.09 |
| α 1.6 | 0.50/0.12 | 0.41/0.07 | 0.33/0.09 | 0.33/0.18 | 0.95/1.00 |
| Cloud at 1 km | 0.46/0.12 | 0.41/0.14 | 0.47/0.31 | 0.71/0.63 | 0.98/1.06 |
| Cloud at 4 km | 0.64/0.25 | 0.56/0.16 | 0.46/0.08 | 0.38/0.04 | 0.27/0.13 |
| Cloud at 6 km | 0.74/0.40 | 0.67/0.29 | 0.58/0.18 | 0.50/0.11 | 0.33/0.02 |
| Cloud at 10 km | 0.90/0.73 | 0.85/0.62 | 0.78/0.48 | 0.72/0.36 | 0.55/0.15 |

What it shows:

- **AOD and cloud height matter most.** With clean air, reds last about a degree longer. With haze they wash out before the Sun sets, and the light is 5 to 8 times dimmer between 1.7° and 0.9°.
- **The height of the aerosol layer comes next.** The same AOD spread higher reaches the light that low clouds receive.
- **Ozone only matters after sunset,** and only for blue. The Ångström exponent barely matters.

## Surface air quality is a different number

An air quality station measures particles (PM2.5) at the ground. The color depends on the whole column the light crosses. The two can move apart:

- A study of a subtropical city in a basin found that surface PM peaks in winter while AOD has a weak annual cycle: the particles grow, but the layer that holds them gets thinner (Escribano and others, 2014).
- The same study suspects satellite AOD there is biased by a wrong estimate of the ground reflectance, which gives a false summer peak.
- Elsewhere the relation is decent on clear days, with R² about 0.6 in the Netherlands, and it changes with place and season.

We found no study that relates PM2.5 to how saturated a sunset looks.

## Where the number could come from

Nothing here is connected. Adding a host is a security decision: see [../data-sources.md](../data-sources.md) and [../threat-model.md](../threat-model.md).

| Source | What it gives | For | Against |
|---|---|---|---|
| [AERONET](https://aeronet.gsfc.nasa.gov/print_web_data_help_v3_new.html) sun photometers | AOD and α, measured through the column | The right quantity, measured. Asking by site name reveals no coordinates | Few sites. No data with clouds. Gaps. Near real time data is not final |
| [CAMS through Open-Meteo](https://open-meteo.com/en/docs/air-quality-api) | AOD forecast every 3 hours, worldwide | Always has a value. No key for non commercial use | A model, in cells of about 45 km that cannot resolve a valley. Needs rounded coordinates |
| Satellite AOD | AOD from space | No new host, through GIBS | A colored image. No data under clouds. Biased over some semi arid surfaces |
| Air quality stations | PM2.5 at the ground | Measured and local | Not the column, see above. APIs vary by country |

A sensible order is to use the measured value when it is recent, the forecast otherwise, and a default of 0.15 with no data. That value is also near what a mid latitude city shows on an ordinary day.

## Limits

- The model has single scattering with a correction, and twilight near the horizon is dominated by multiple scattering. It should be trusted less the deeper the Sun is.
- Its aerosol parameters were not fitted: photos cannot measure them, see [sky-color.md](sky-color.md).
- The sensitivity table is the model talking, not measurements.
- METAR gives the lowest cloud layer at an airport, which may not be the layer you are looking at.

## Sources

- [Corfidi, NOAA: The colors of twilight and sunset](https://www.spc.noaa.gov/publications/corfidi/sunset/)
- [Saito, Iwabuchi and Hayasaka, 2013: tropospheric aerosol and twilight sky color](https://www.jstage.jst.go.jp/article/sola/9/0/9_2013-004/_article/-char/en)
- [Zerefos and others, 2014: red to green ratios in paintings](https://acp.copernicus.org/articles/14/2987/2014/)
- Lee and Hernández-Andrés, 2003: Measuring and modeling twilight's purple light, Applied Optics
- [Atmospheric ozone and colors of the Antarctic twilight sky, 2011](https://www.scilit.net/publications/2eca4a98437bf41f469eddd0864ed0cc)
- Escribano, Gallardo, Rondanelli and Choi, 2014: Satellite retrievals of aerosol optical depth over a subtropical urban area, Aerosol and Air Quality Research 14: 596-607
- [AOD and PM2.5 in the Netherlands](https://acc.pbl.nl/en/node/3325)
- [Air mass and the Kasten and Young formula](https://en.wikipedia.org/wiki/Air_mass_(astronomy))
- Hansen and Travis, 1974: Light scattering in planetary atmospheres, Space Science Reviews

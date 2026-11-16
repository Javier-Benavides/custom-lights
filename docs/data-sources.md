# Data sources

Three public sources, with no API keys. All of them are optional: with no data, the scenes go on with the Sun's position and sensible defaults.

| Data | Source | Frequency | What leaves your machine |
|---|---|---|---|
| Observed weather | [aviationweather.gov](https://aviationweather.gov/data/api/) (NOAA) | Hourly | The ICAO codes of your stations |
| Cloud cover from space | [gibs.earthdata.nasa.gov](https://nasa-gibs.github.io/gibs-api-docs/access-advanced-topics/) (NASA) | Hourly | A latitude and longitude box |
| Solar activity | [services.swpc.noaa.gov](https://services.swpc.noaa.gov/text/daily-solar-indices.txt) (NOAA) | Daily | Nothing |

Every request goes through `luces/data/fetch.py`: HTTPS only, 20 s, at most 64 KB, and a generic user agent.

## Not connected yet

Aerosol depth would help the colors, and [physics/atmosphere.md](physics/atmosphere.md) compares where it could come from. Each option means a new host, which is a security decision: say which domain, how often and what data leaves.

## Privacy

Your location is the only private thing here. It lives in `/var/lib/luces/control/place.toml`, never in the repository.

- Use one decimal: the Sun needs no more.
- The airport codes and the satellite box say roughly where you are, to the services above.
- `luces status` prints the raw METAR, which names your airport. Remove it before pasting into an issue.
- A timed photo with a Sun altitude reveals a location. Share altitude, direction and color, not the place and time.

## Observed weather: METAR

A METAR is what a station observed that hour. Forecasts are not used: this project shows what the sky is doing, not what it might do. Everything after `NOSIG`, `TEMPO`, `BECMG` or `RMK` is dropped for that reason.

```text
METAR ZZZZ 051400Z 18008KT 5000 -RA BKN015 OVC030 12/10 Q1012
```

| Group | Becomes |
|---|---|
| `051400Z` | Day 5 at 14:00 UTC |
| `BKN015`, `OVC030` | Coverage of the most covered layer, and its height in hundreds of feet |
| `-RA` | `kind`: rain, snow, fog, haze or storm |
| `12/10` | Temperature, for the satellite |

Coverage: `FEW` 20 %, `SCT` 45 %, `BKN` 75 %, `OVC` 100 %. From 12,000 feet up clouds are thin, so they weigh 60 %.

Stations are tried in order, and one older than 2 hours gives way to the next: some aerodromes do not report at night.

## Cloud cover from space: GOES

`CAVOK` only speaks of what is under 1500 m or the minimum sector altitude, so an airport can report a clear sky under high clouds. The satellite fills that gap: the program uses the greater of both.

`luces/data/satellite.py` asks NASA GIBS for a 48×48 infrared image of the box in `place.toml`. In this image brighter is colder, and the coldest comes in color. A pixel is cloud if it is clearly brighter than the ground, or colder than the air by `margin_k`. Both tests are needed, because each one fails alone: with everything covered there is no ground to compare with.

The layer is GOES-East, which covers the Americas. Other regions need another layer.

Keep tall mountains out of the box: a mountain looks as cold as a cloud. The scale from gray to temperature was estimated from sample images: NASA does not publish it.

## Solar activity: NOAA

A text file with a row per day: 10.7 cm flux, sunspot number, area and flares by class. `-999` means no data. It is fetched at most every 20 hours.

## Adding a source

1. Write a parser in `luces/data/`: text or bytes in, a dict out, with no network.
2. Add the fetch to `update.py`, and the host to `ALLOWED_HOSTS` in `tests/test_architecture.py`.
3. Say here what leaves the machine. A new host is a security decision and needs a maintainer: see [threat-model.md](threat-model.md).

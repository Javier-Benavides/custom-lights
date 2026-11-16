"""Where the Sun is, from the clock and the place, with no network and no packages.

NOAA's formulas, based on Meeus, Astronomical Algorithms: accurate to a minute between latitudes ±72°.
Theory and sources: docs/physics/sun-position.md.
"""
import functools
import math

HORIZON = -0.833   # at this altitude the Sun is seen to rise and set, because of refraction


def sun_altitude(epoch, lat, lon):
    """Degrees above the horizon, without refraction. `epoch` is UTC seconds, and `lon` is positive to the east."""
    century = (epoch / 86400 + 2440587.5 - 2451545) / 36525
    mean_longitude = (280.46646 + century * (36000.76983 + century * 0.0003032)) % 360
    anomaly = math.radians(357.52911 + century * (35999.05029 - 0.0001537 * century))
    eccentricity = 0.016708634 - century * (0.000042037 + 0.0000001267 * century)
    center = (math.sin(anomaly) * (1.914602 - century * (0.004817 + 0.000014 * century))
              + math.sin(2 * anomaly) * (0.019993 - 0.000101 * century)
              + math.sin(3 * anomaly) * 0.000289)
    omega = math.radians(125.04 - 1934.136 * century)
    apparent_longitude = math.radians(mean_longitude + center - 0.00569 - 0.00478 * math.sin(omega))
    seconds = 21.448 - century * (46.815 + century * (0.00059 - century * 0.001813))
    obliquity = math.radians(23 + (26 + seconds / 60) / 60 + 0.00256 * math.cos(omega))
    declination = math.asin(math.sin(obliquity) * math.sin(apparent_longitude))

    y = math.tan(obliquity / 2) ** 2
    l0 = math.radians(mean_longitude)
    equation_of_time = 4 * math.degrees(
        y * math.sin(2 * l0) - 2 * eccentricity * math.sin(anomaly)
        + 4 * eccentricity * y * math.sin(anomaly) * math.cos(2 * l0)
        - 0.5 * y * y * math.sin(4 * l0) - 1.25 * eccentricity ** 2 * math.sin(2 * anomaly))

    solar_minutes = ((epoch % 86400) / 60 + equation_of_time + 4 * lon) % 1440
    hour_angle = math.radians(solar_minutes / 4 - 180)
    latitude = math.radians(lat)
    sine = (math.sin(latitude) * math.sin(declination)
            + math.cos(latitude) * math.cos(declination) * math.cos(hour_angle))
    return math.degrees(math.asin(max(-1.0, min(1.0, sine))))


def crossing(start, end, altitude, lat, lon):
    """When the Sun reaches that altitude, between two instants when it only rises or only sets. None if it does not."""
    first = sun_altitude(start, lat, lon) - altitude
    if first * (sun_altitude(end, lat, lon) - altitude) > 0:
        return None
    for _ in range(20):
        middle = (start + end) / 2
        if first * (sun_altitude(middle, lat, lon) - altitude) > 0:
            start = middle
        else:
            end = middle
    return end


@functools.lru_cache(maxsize=8)
def _last_sunset(epoch, lat, lon):
    step, t = 600.0, float(epoch)
    after = sun_altitude(t, lat, lon)
    for _ in range(26 * 6):
        before = sun_altitude(t - step, lat, lon)
        if before >= HORIZON > after:
            low, high = t - step, t
            for _ in range(7):
                middle = (low + high) / 2
                low, high = (middle, high) if sun_altitude(middle, lat, lon) >= HORIZON else (low, middle)
            return high
        t, after = t - step, before
    return None


def last_sunset(epoch, lat, lon):
    """The last sunset, for use with the Sun already below the horizon. None if there was none, near the poles.

    Rounded forward to 10 minutes to reuse the calculation. Rounding back would fail: just after sunset, the search
    would start before it and find yesterday's.
    """
    return _last_sunset((int(epoch // 600) + 1) * 600, lat, lon)

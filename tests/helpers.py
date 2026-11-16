"""What several tests share. All the coordinates here are made up on purpose."""
import calendar
import math
import os

from luces import scenes, settings

PLACE = {"lat": 10.0, "lon": 20.0, "stations": ["ZZZZ"]}
SOUTH = {"lat": -40.0, "lon": 10.0, "stations": []}
SETTINGS = settings.load(os.devnull)


def epoch(*date):
    return calendar.timegm((*date, 0))


def distance(a, b):
    return max(abs(x - y) for x, y in zip(a, b))


def ctx_at(t, **extra):
    return scenes.Context(t, SETTINGS, PLACE, **extra)


def one_day():
    start = epoch(2026, 3, 20, 0, 0, 0)
    return [start + m * 60 for m in range(0, 1440, 5)]


def correlation(a, b):
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    return (sum((x - ma) * (y - mb) for x, y in zip(a, b))
            / math.sqrt(sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b)))


def autocorrelation(series, lag):
    mean = sum(series) / len(series)
    x = [v - mean for v in series]
    return sum(a * b for a, b in zip(x, x[lag:])) / sum(a * a for a in x)


def band_power(series, step_s, low_hz, high_hz):
    """The mean power of a band of frequencies."""
    mean = sum(series) / len(series)
    x = [v - mean for v in series]
    total = 0.0
    for k in range(10):
        w = 2 * math.pi * (low_hz + (high_hz - low_hz) * k / 9) * step_s
        total += sum(v * math.cos(w * i) for i, v in enumerate(x)) ** 2 + sum(v * math.sin(w * i) for i, v in enumerate(x)) ** 2
    return total / 10

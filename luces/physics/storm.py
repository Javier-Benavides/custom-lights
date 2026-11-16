"""Lightning: when it strikes and how each strike fades.

Strikes are drawn per hour from a fixed seed, so any instant can be computed without history.
Theory and sources: docs/physics/storm.md.
"""
import functools
import math
import random

STROKES = (1, 1, 2, 2, 3)   # a real bolt flickers: 1 to 3 strokes, never more than 3 in a second
FADE_PER_ZONE = 0.55        # how much of a stroke reaches the next zone
ZONE_DELAY_S = 0.03


@functools.lru_cache(maxsize=16)
def strikes_in_hour(hour, rate, zones=3):
    """(start, zone, ((delay, strength), …)) for each strike of that hour."""
    rng = random.Random(hour * 7919 + 3)
    count = int(rate) + (1 if rng.random() < rate - int(rate) else 0)
    strikes = []
    for _ in range(count):
        strokes, delay = [], 0.0
        for _ in range(rng.choice(STROKES)):
            strokes.append((delay, rng.uniform(0.6, 1.0)))
            delay += rng.uniform(0.12, 0.3)
        strikes.append((hour * 3600 + rng.uniform(0, 3600), rng.randrange(zones), tuple(strokes)))
    return tuple(strikes)


def strikes_near(t, rate, zones=3):
    """The strikes of this hour and the last one."""
    hour = int(t // 3600)
    return strikes_in_hour(hour - 1, rate, zones) + strikes_in_hour(hour, rate, zones)


def flash_at(t, strikes, fade_s, zones=3):
    """{zone: strength from 0 to 1}, only for the zones lit now. A strike is born in one zone and reaches the rest weaker."""
    lit = {}
    for start, origin, strokes in strikes:
        if not -1.0 < t - start < 2.0:
            continue
        for zone in range(zones):
            distance = abs(zone - origin)
            for delay, strength in strokes:
                age = t - start - delay - ZONE_DELAY_S * distance
                if 0 <= age <= 5 * fade_s:
                    lit[zone] = max(lit.get(zone, 0.0), strength * FADE_PER_ZONE ** distance * math.exp(-age / fade_s))
    return lit

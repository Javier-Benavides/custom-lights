"""The Sun's real activity turned into events: dark sunspots and bright flares.

Events are drawn per hour from a fixed seed, so any instant can be computed without history.
Theory and sources: docs/physics/solar-activity.md.
"""
import bisect
import functools
import math
import random

from .basics import clamp

SPREAD = 0.6          # how much of an event reaches the next zone
SPOT_DELAY_S = 10     # how long a sunspot takes to reach the next zone
FLARE_DELAY_S = 3     # and a flare


def activity_from_flux(flux, quiet, active):
    """From 0 to 1, from the 10.7 cm radio flux of a quiet and a very active Sun."""
    return clamp((flux - quiet) / (active - quiet))


@functools.lru_cache(maxsize=16)
def events_in_hour(hour, rate, seed, zones=3):
    """(start, zone, strength), sorted by start. Strength follows a power law: many small and few big, like real
    flares, whose frequency falls with energy with a slope near 1.8."""
    rng = random.Random(hour * 1000003 + seed)
    count = int(rate) + (1 if rng.random() < rate - int(rate) else 0)
    return tuple(sorted((hour * 3600 + rng.uniform(0, 3600), rng.randrange(zones),
                         min(1.0, 0.05 * (1 - rng.random()) ** -1.25)) for _ in range(count)))


def events_near(t, rate, seed, lasting_s, zones=3):
    """Events born in the last `lasting_s` seconds. Walking all of them on every frame would be the slowest step."""
    hour = int(t // 3600)
    events = events_in_hour(hour - 1, round(rate, 3), seed, zones) + events_in_hour(hour, round(rate, 3), seed, zones)
    return events[bisect.bisect(events, (t - lasting_s,)):bisect.bisect(events, (t,))]


def sunspot_shape(age, duration_s):
    return math.sin(math.pi * age / duration_s) ** 2 if 0 <= age <= duration_s else 0.0


def flare_shape(age, rise_s, fall_s):
    """Rises fast and falls slowly. The rise takes seconds: it is a wave of light, not a flash."""
    if age < 0 or age > rise_s + 6 * fall_s:
        return 0.0
    if age < rise_s:
        return 0.5 - 0.5 * math.cos(math.pi * age / rise_s)
    return math.exp(-(age - rise_s) / fall_s)


def sunspot_at(t, zone, events, duration_s):
    """From 0 to 1: how dark a zone is at `t`."""
    return max((SPREAD ** abs(zone - origin) * sunspot_shape(t - start - SPOT_DELAY_S * abs(zone - origin), duration_s)
                for start, origin, _ in events), default=0.0)


def flare_at(t, zone, events, rise_s, fall_s):
    """From 0 to 1: how much flare reaches a zone at `t`. Stronger flares last longer."""
    return max((strength * SPREAD ** abs(zone - origin)
                * flare_shape(t - start - FLARE_DELAY_S * abs(zone - origin), rise_s, fall_s * (0.5 + strength))
                for start, origin, strength in events), default=0.0)

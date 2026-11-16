"""How a campfire moves: three independent rhythms, plus the fire that combines them.

    Embers   tens of seconds   the bed of coals slowly brightens and fades
    Gusts    a few seconds     air feeds the fire and makes the next tongues bigger
    Tongues  about 2 a second  each flame licks up fast and dies slowly

Each one is a pattern on its own: call it with a time and use the number for anything.
`Campfire` adds them into a single heat, because in a fire the brightest part is also the yellowest.
Theory, measurements and sources: docs/physics/fire.md.
"""
import math
from dataclasses import dataclass

from .basics import clamp, smoothstep
from .noise import even_noise, hash_noise

BIRTH_JITTER = 0.45   # a tongue is born anywhere in its turn: the rhythm is felt, but cannot be counted
BASE_HEAT = 0.06
EMBER_HEAT = 0.2
GUST_HEAT = 0.12
SHARED_TONGUES = 0.75   # the rest of the tongues belong to each zone alone
GUST_FLOOR = 0.4        # how much of a tongue survives with no gust at all
ZONE_SEED = 40


def tongue_sum(t, every_s, fall_s, rise_s, seed):
    """The sum of the tongues alive at `t`, from 0 to a little over 1. Most are small and a few are tall.
    Pulses that rise fast and fall slowly give the spectrum measured in flames: 1/f² above their rhythm."""
    current = math.floor(t / every_s)
    total = 0.0
    for i in range(current - math.ceil(5 * fall_s / every_s) - 1, current + 2):
        age = t - (i + BIRTH_JITTER * hash_noise(i, seed)) * every_s
        if age > 0:
            height = 0.1 + 0.9 * (0.5 + 0.5 * hash_noise(i, seed + 1)) ** 2
            total += height * smoothstep(age / rise_s) * math.exp(-age / fall_s)
    return total


@dataclass(frozen=True)
class Embers:
    """From 0 to 1: the slow glow of the coals."""
    period_s: float = 30.0
    seed: int = 1

    def __call__(self, t):
        return even_noise(t, self.period_s, self.seed, 3)


@dataclass(frozen=True)
class Gusts:
    """From 0 to 1: how much air is feeding the fire."""
    period_s: float = 6.0
    seed: int = 2

    def __call__(self, t):
        return even_noise(t, self.period_s, self.seed, 3)


@dataclass(frozen=True)
class Tongues:
    """From 0 to a little over 1: flames licking up. `every_s` follows the flicker of a pool of fire of diameter D,
    1.5/√D Hz with D in metres: 0.45 s is a fire of 46 cm."""
    every_s: float = 0.45
    fall_s: float = 0.3
    rise_s: float = 0.06
    seed: int = 3

    def __call__(self, t):
        return tongue_sum(t, self.every_s, self.fall_s, self.rise_s, self.seed)


@dataclass(frozen=True)
class Restlessness:
    """From 0.5 to 1.5: a multiplier for calm stretches and lively ones."""
    period_s: float = 60.0
    seed: int = 7

    def __call__(self, t):
        return 0.5 + even_noise(t, self.period_s, self.seed)


@dataclass(frozen=True)
class Flame:
    heat: float   # from 0 to 1: decides color and brightness together
    size: float   # from 0 to 1: the tongues alone


@dataclass(frozen=True)
class Campfire:
    embers: Embers = Embers()
    gusts: Gusts = Gusts()
    tongues: Tongues = Tongues()

    def at(self, t, strength=1.0, zone=0, delay_s=0.0):
        """The fire in one zone. `strength` scales the tongues, and `delay_s` is how late the fire reaches this zone."""
        here = t - delay_s
        ember, gust = self.embers(here), self.gusts(here)
        shared = self.tongues(here)
        own = tongue_sum(t, self.tongues.every_s, self.tongues.fall_s, self.tongues.rise_s, ZONE_SEED + zone)
        size = clamp(SHARED_TONGUES * shared + (1 - SHARED_TONGUES) * own) * (GUST_FLOOR + (1 - GUST_FLOOR) * gust)
        return Flame(clamp(BASE_HEAT + EMBER_HEAT * ember + GUST_HEAT * gust + strength * size), size)

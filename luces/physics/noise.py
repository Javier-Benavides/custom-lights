"""Stateless noise: the value at an instant depends only on the instant and the seed.

That is what lets a scene be simulated, tested and replayed without keeping any history.
Theory: docs/physics/noise.md.
"""
import bisect
import functools
import math

from .basics import clamp

SWELLS = ((1.0, 0.5), (0.62, 0.3), (0.38, 0.2))   # length and weight of each swell: lengths that never line up


def hash_noise(i, seed):
    """From -1 to 1, a function of `i` and `seed` only: randomness with no memory."""
    x = (i * 0x9E3779B1 + seed * 0x85EBCA77) & 0xFFFFFFFF
    x = ((x ^ (x >> 15)) * 0x2C1B3C6D) & 0xFFFFFFFF
    x = ((x ^ (x >> 12)) * 0x297A2D39) & 0xFFFFFFFF
    return (x ^ (x >> 15)) / 0x7FFFFFFF - 1.0


def fractal_noise(t, period_s, seed=0, octaves=5):
    """From -1 to 1, with no rhythm: each octave lasts half as long as the last and weighs less.
    Unlike a sum of sines it never repeats, so the eye finds no pattern."""
    total = weight = 0.0
    strength = 1.0
    for octave in range(octaves):
        x = t / period_s * 2 ** octave + 17.3 * octave
        i = math.floor(x)
        f = x - i
        f = f * f * (3 - 2 * f)
        a, b = hash_noise(i, seed + 31 * octave), hash_noise(i + 1, seed + 31 * octave)
        total += strength * (a + (b - a) * f)
        weight += strength
        strength *= 0.6
    return total / weight


@functools.lru_cache(maxsize=32)
def _distribution(seed, octaves):
    return sorted(fractal_noise(i * 0.37, 1.0, seed, octaves) for i in range(8000))


def even_noise(t, period_s, seed, octaves=4):
    """Like `fractal_noise`, from 0 to 1 and evenly spread: it spends the same time at every value.
    So "below 0.7" is true 70 % of the time, and a palette gets used end to end."""
    distribution = _distribution(seed, octaves)
    return bisect.bisect(distribution, fractal_noise(t, period_s, seed, octaves)) / len(distribution)


def swells(t, period_s, irregularity, seed):
    """From 0 to 1: waves of different height and length. Each one stretches and shrinks its own cycles, and
    their sum gives tall peaks, small peaks and nearly still moments, with no two stretches alike."""
    total = 0.0
    for i, (length, weight) in enumerate(SWELLS):
        phase = t / (period_s * length) + irregularity * fractal_noise(t, period_s * length * 4, seed + i, 3)
        total += weight * math.sin(2 * math.pi * phase + 2.1 * i)
    return clamp(0.5 + 0.6 * total)

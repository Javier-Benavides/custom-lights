"""Paced breathing: the shape of a breath, and a rhythm that slows down without a jump.

Evidence and sources: docs/physics/breathing.md.
"""
import math


def breath_shape(seconds, inhale_s, exhale_s):
    """From 0 to 1: rises in `inhale_s` and falls in `exhale_s`, with no corners."""
    p = seconds % (inhale_s + exhale_s)
    if p < inhale_s:
        return 0.5 - 0.5 * math.cos(math.pi * p / inhale_s)
    return 0.5 + 0.5 * math.cos(math.pi * (p - inhale_s) / exhale_s)


def breaths_taken(seconds, start_s, end_s, slowdown_s):
    """How many breaths have gone by, if each one stretches little by little from `start_s` to `end_s` during
    `slowdown_s` seconds. It is the integral of the rhythm: that is what lets a pulse slow down without a jump."""
    seconds = max(0.0, seconds)
    if slowdown_s <= 0 or end_s == start_s:
        return seconds / end_s
    k = (end_s - start_s) / slowdown_s
    return math.log(1 + k * min(seconds, slowdown_s) / start_s) / k + max(0.0, seconds - slowdown_s) / end_s

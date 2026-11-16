"""Small helpers shared by the physics modules."""


def clamp(x, low=0.0, high=1.0):
    return max(low, min(high, x))


def smoothstep(x):
    """0 below 0, 1 above 1, and an S-curve with flat ends in between."""
    x = clamp(x)
    return x * x * (3 - 2 * x)


def mix(a, b, x):
    """Linear blend of two tuples: `a` at x = 0, `b` at x = 1."""
    return tuple(p + (q - p) * x for p, q in zip(a, b))

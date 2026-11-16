# Instructions for this folder

This package is the part of the project meant to be reused. Read `AGENTS.md` at the root first.

## The contract

- Import only the standard library and modules of this package. `tests/test_architecture.py` enforces it.
- No clock, no files, no network, no settings, no global state that changes. Time is an argument.
- Units: seconds, degrees, colors as `(r, g, b)` from 0 to 1. Put the unit in the name: `fall_s`, `height_km`.
- The same arguments always give the same result. Randomness comes from `noise.hash_noise` or a seeded `random.Random`.

## A new pattern

```python
@dataclass(frozen=True)
class Crackles:
    """From 0 to 1: what it models, in one line."""
    every_s: float = 3.0
    seed: int = 11

    def __call__(self, t):
        ...
```

1. Defaults must give something sensible, so `Crackles()(t)` just works.
2. Add a test in `tests/physics/` that uses it with no settings and no scene.
3. Add it to the page in `docs/physics/`: what happens, the model, how to reuse it, sources, limits.
4. Say where each number comes from: a source, a measurement, or "design choice".

## Changing an existing model

Changing a default changes what people see. Scenes were tuned by eye on real LEDs, so say in the PR that it needs `needs-eyes`.

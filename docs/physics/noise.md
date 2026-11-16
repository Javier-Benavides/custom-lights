# Noise with no memory

Nature does not repeat. A sum of sine waves does, and the eye finds the pattern within minutes.

## The model

| Function | Range | Use |
|---|---|---|
| `hash_noise(i, seed)` | -1 to 1 | The base: a number from an integer, with no state |
| `fractal_noise(t, period_s, seed, octaves)` | -1 to 1 | Motion with no rhythm: each octave lasts half as long and weighs 60 % |
| `even_noise(t, period_s, seed, octaves)` | 0 to 1 | The same, spread evenly: it spends equal time at every value |
| `swells(t, period_s, irregularity, seed)` | 0 to 1 | Waves with different heights and lengths, for slow calm motion |

**Why even noise matters.** Fractal noise spends most of its time near the middle. Remapped through its own distribution, "below 0.7" is true 70 % of the time, which is what makes cloud coverage exact and makes a palette get used end to end.

**Why no memory.** Each function depends only on `t` and `seed`. That lets a scene be tested, simulated for a whole day and replayed exactly, and keeps the scenes stateless.

## Use it elsewhere

```python
from luces.physics.noise import even_noise, swells
level = even_noise(time.time(), period_s=10.0, seed=5)
```

## Limits

`even_noise` builds its distribution on first use, once per seed and octave count: about 8000 evaluations.

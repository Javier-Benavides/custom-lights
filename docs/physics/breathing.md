# Slow breathing

The `relax` and `breathe` scenes are built on the best evidence available on light and calm, which is mostly about breathing, not color.

## What happens

| Evidence | Study | In the code |
|---|---|---|
| Slow breathing raises heart rate variability, during and after | [Laborde 2022](https://pure.solent.ac.uk/en/publications/effects-of-voluntary-slow-breathing-on-heart-rate-and-heart-rate-/), meta-analysis of 223 studies | 6 breaths a minute |
| Exhaling longer than inhaling gave more relaxation | [Van Diest 2014](https://hero.epa.gov/hero/index.cfm/reference/details/reference_id/3980498), 30 people | Inhale 3 s, exhale 7 s |
| A breathing guide in the periphery slowed breathing without asking for attention | [Moraveji 2011](https://idl.uw.edu/papers/peripheral-paced-respiration) | A soft change, no need to stare |
| A subtle oscillation slower than the person's breathing slowed it, unprompted | [BrightBeat, Ghandeharioun and Picard 2017](https://www.media.mit.edu/publications/brightbeat-effortlessly-influencing-breathing-for-cultivating-calmness-and-focus/) | The hidden pulse in `relax` |
| A dim light rising and falling in 90 s cycles raised parasympathetic activity more than a fixed one | [Chen 2021](https://doi.org/10.1155/2021/6697701), 21 people | Slow waves of brightness |
| 1/f fluctuation lowered the pulse against normal light and random flashes | [Doi 1997](https://www.jstage.jst.go.jp/article/ieejeiss1987/117/4/117_4_409/_article/-char/en), small study | Irregular waves, not a perfect sine |
| Brightness and saturation raise arousal as much as hue | [Wilms and Oberfeld 2018](https://pubmed.ncbi.nlm.nih.gov/28612080/), 62 people | Low brightness, medium saturation |

## The model

`breath_shape` gives one breath, rising and falling with no corners.

`breaths_taken` is the hidden pulse: it starts near a normal rhythm, 12 breaths a minute, and stretches each breath until it reaches 6 a minute in 12 minutes. It is the integral of the rhythm, which is what lets it slow down with no jump.

`relax` adds [swells](noise.md) of brightness and color with no two cycles alike, under a pulse of ±12 %.

## In the code

`luces/physics/breathing.py`, and `luces/scenes/relax.py` and `breathe.py`.

## Use it elsewhere

```python
from luces.physics.breathing import breath_shape, breaths_taken
level = breath_shape(seconds, inhale_s=3, exhale_s=7)
```

## Limits

- Except for the breathing meta-analysis, these are small studies.
- They lit a whole room or used a screen and sound. None tested PC fans: expect a weaker effect.
- `relax` works as a background. `breathe` only works if you follow it.
- Personal preference matters. The default palette is green and white because blue did not feel relaxing to the author, even if color studies lean towards blue.

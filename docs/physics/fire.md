# Campfire

How to move a light so it feels like fire. In luces the colors of the `sun` scene come from the real Sun, and the motion comes from here.

## What happens

A fire is not one flicker. It is three rhythms stacked:

| Layer | Pattern | Rhythm | Evidence |
|---|---|---|---|
| The bed of coals slowly glows and fades | `Embers` | Tens of seconds | Flame brightness approaches 1/f below 0.1 Hz |
| Air feeds the fire and the next flames grow | `Gusts` | A few seconds | Design, with no measurement of its own |
| Flames lick up and die | `Tongues` | About 2 a second | Flames pulse at 1.5/√D Hz, with D in metres |

Three more things matter, and they are not about rhythm:

- **Color and brightness go together.** One heat picks both, as in FastLED's Fire2012: the brightest part is also the yellowest.
- **Fire rolls.** In theatre this comes from red and amber sources that do not move together. Here the fire reaches each zone a little later, and each zone keeps a quarter of its tongues to itself.
- **You see the light of the fire, not the flame.** Stage lighting designers point at what the fire throws on a wall. With few LEDs that is the right target.

## The model

**Tongues.** The flicker of a pool of fire of diameter D follows `f ≈ 1.5/√D` Hz (D in metres). For a campfire of 46 cm that is 2.2 Hz, so `every_s = 0.45`.

Each tongue is a pulse that rises in 0.06 s and falls in 0.3 s. A sum of such pulses is shot noise, and it has the spectrum measured in flames: flat at low frequencies, and 1/fⁿ above, with n = 2.12 ± 0.7. Heights follow a skewed distribution, so most are small and few are tall. Each tongue is born anywhere in its turn: an earlier version kept them regular and showed a 5 dB peak at 2.2 Hz, which feels like a metronome.

**Embers and gusts** are evenly spread fractal noise, with periods of 30 s and 6 s.

**Restlessness** is a multiplier between 0.5 and 1.5 that gives calm and lively stretches.

**Campfire** adds them into one heat:

```text
size = clamp(0.75·shared tongues + 0.25·own tongues) · (0.4 + 0.6·gust)
heat = clamp(0.06 + 0.2·embers + 0.12·gust + strength·size)
```

Fire2012 keeps state in an array of cells. Here nothing is stored: each tongue comes from a hash of its turn, so an instant always gives the same result.

## In the code

`luces/physics/fire.py`: `Embers`, `Gusts`, `Tongues`, `Restlessness` and `Campfire`.

`luces/scenes/sun.py` feeds `strength` from solar activity, and takes the color from the palette.

Frame rate matters: at 4 frames a second the eye cannot get more than 2 changes a second, so the `sun` scene runs at 15 and smooths for only 0.04 s.

## Use it elsewhere

Each pattern works alone. Call it with a time and use the number for anything:

```python
from luces.physics.fire import Campfire, Tongues

candle = Tongues(every_s=0.2, fall_s=0.1)   # a smaller flame flickers faster
level = candle(time.time())

fire = Campfire(tongues=Tongues(every_s=0.7))   # a bonfire of about a metre
flame = fire.at(time.time(), strength=1.5)
print(flame.heat, flame.size)
```

[`examples/fire_in_terminal.py`](../../examples/fire_in_terminal.py) draws it in a terminal.

## Measured here

In simulation, through the same path as the service, for the `sun` scene:

| What | Result | Expected |
|---|---|---|
| Fall above 3 Hz | 1/f^2.2 | n = 2.12 ± 0.7 |
| Peak at the rhythm of the tongues | None: 2.24 Hz is 1 dB under the next band | No metronome |
| Brightness, 10 % to 90 % | 0.42 to 0.64 | Visible at a glance |
| Worst second in 2 h | 2.5 flashes | 3 at most |

## Limits

- No measurements of a real wood fire were found: the data come from candles, laboratory flames and pool fires. The formula 1.5/√D does fit a wide range of sizes.
- The candle spectrum of Fujiwara and Tsuge was read from a summary, because the PDF did not open.
- The lengths of gusts and embers are design.
- A flame of 2 Hz sits just under the 3 flashes a second limit: lowering `tongue_s` under 0.45 is refused by settings. See [../decisions.md](../decisions.md).

## Sources

- [Flicker frequency of buoyant flames, 1.5/√D](https://arxiv.org/pdf/1803.10400)
- [Review of the pulsation of pool fires](https://repository.lboro.ac.uk/articles/journal_contribution/A_review_of_research_and_experimental_study_on_the_pulsation_of_buoyant_diffusion_flames_and_pool_fires/9547682)
- [Fujiwara and Tsuge: brightness of candle flames](https://nitech.repo.nii.ac.jp/record/2146/files/bnit1997_189.pdf)
- [An LED candle with realistic dynamics, Cornell](https://people.ece.cornell.edu/land/courses/eceprojectsland/STUDENTPROJ/2001to2002/pc59/)
- [FastLED: the Fire2012 example](https://github.com/FastLED/FastLED/tree/master/examples/Fire2012)
- [Fire on lighting consoles](https://community.etcconnect.com/control_consoles/legacy-consoles/f/legacy---wholehog-3/50269/htp-with-effects) · [with incandescents](https://community.etcconnect.com/architectural_controls/f/mosaic-show-control/1542/fire-effect-with-incandescents)

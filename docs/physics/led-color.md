# From a physical color to LED bytes

A formula can tell what color the light is. It cannot tell what bytes make these LEDs look like that color to a person in a room. Those are separate problems, and mixing them is how the tables ended up set by hand.

This page is research. `luces/color.py` only applies gamma today.

## Three layers

```text
atmosphere ──> spectrum ──> CIE XYZ        physics: same for everyone
XYZ ──> linear LED values                  device: depends on your LEDs
linear LED values ──> final bytes          look: a choice, with few parameters
```

## What is known about the device

- Data sheets for WS2812 class LEDs give wavelengths of 620 to 630 nm for red, 515 to 530 nm for green and 465 to 475 nm for blue, and intensities of 550 to 700, 1100 to 1400 and 200 to 400 mcd. They give no chromaticity coordinates.
- The LEDs in a fan are often an unknown part behind a diffuser.
- A rough spectrum for each LED gives xy of about (0.70, 0.30), (0.15, 0.77) and (0.12, 0.06). From those and the data sheet intensities, a neutral white should need green/red 1.09 and blue/red 0.58.
- On real fans that is wrong: to look white, green goes clearly below red, and blue close to red. FastLED's typical correction, 255, 176, 240, is much nearer.

**So data sheets are not enough. The device layer has to be measured.**

## What a trial showed

Physical color against the colors chosen by eye on real fans, as green/red in linear light:

| Sun altitude | Physical | Data sheet matrix | Same, balanced to the observed white | Chosen by eye |
|---|---|---|---|---|
| 6.5° | 0.69 | 0.91 | 0.58 | 0.54 |
| 5° | 0.62 | 0.86 | 0.54 | 0.49 |
| 2.2° | 0.40 | 0.66 | 0.42 | 0.38 |
| 0.8° | 0.23 | 0.45 | 0.28 | 0.19 |

- **Green is close once balanced to the white.** That part looks like physics.
- **Blue is not.** Physical gold has 20 to 30 % of blue relative to red. On these LEDs, 8 to 10 % already looks peach, and the gold people accepted has under 2 %.
- A simple rule, squaring blue/red, seemed to fit at first. It stopped fitting when the sky was sampled in other directions: **do not use it.**

## What may explain the blue

Unproven, in order of how much we trust them:

- **Saturation by choice.** A real sky is pale. The tables are more saturated on purpose, see [sky-color.md](sky-color.md). The eye remembers gold, and the air is not gold everywhere.
- **Spectrum.** A few narrow LEDs are not the broad light of the sky, and the same XYZ can look different on them.
- **Dim rooms.** Between about 0.01 and 3 cd/m², rods start to work, and sensitivity moves toward blue and green: the Purkinje effect. That could make low blue count for more. Nobody measured the luminance here.

## How to calibrate

1. Measure the three primaries with a colorimeter, or match each one against a calibrated screen by eye.
2. Fit a 3×3 matrix from XYZ to linear LED values, with the observed white as a check.
3. Add one saturation parameter for the look, and keep it visible in the settings.
4. Keep some of the chosen colors out of the fit, and test on them.

## Rules for contributors

- Never tune colors from a phone photo of the LEDs. Phones clip them and balance them. A person in the room is the instrument.
- A photo can compare the sky with the sky, not the LEDs with the sky.
- Results for one set of LEDs belong in settings, not in the physics.

## Sources

- [WS2812B data sheet](https://cdn.shopify.com/s/files/1/0174/1800/files/WS2812B-LED-datasheet.pdf)
- [Purkinje effect](https://en.wikipedia.org/wiki/Purkinje_effect)

# The color of a clear sky

Is there a formula that gives the color of the sky from the angle of the Sun? There are several models, and none is a single formula: the color depends on where you look, on aerosols, on ozone and on clouds.

## What happens

- **Rayleigh scattering:** air scatters short wavelengths far more than long ones, as λ⁻⁴. That is why the day sky is blue.
- **Long paths:** with the Sun low, its light crosses much more air, loses the blue on the way and arrives yellow, orange and red.
- **Ozone:** the Chappuis band absorbs orange and yellow. With the Sun near the horizon it matters as much as Rayleigh: at a solar zenith angle of 90°, about two thirds of the blue at the zenith is due to ozone (Lange and others, 2023).
- **Aerosols:** they scatter all colors forward, and whiten the sky near the Sun.
- **The Earth's shadow:** after sunset, the lower atmosphere goes dark while the upper part stays lit.

## Models that exist

| Model | Works from | Note |
|---|---|---|
| Preetham, 1999 | Sun above the horizon | Criticized for low Suns |
| Hosek-Wilkie, 2012 | 0° | Stops just where twilight starts |
| Prague, 2021 | -4.2° | The best of these, but stops before twilight ends |
| SKYCOLOR, Gedzelman 2005 | Includes twilight | Curved Earth, refraction and ozone. The approach used here |
| Bruneton, 2017 | Includes twilight | Source of the solar spectrum and ozone data used here |

## The model here

`luces/physics/sky_model.py`, in pure Python: a spherical atmosphere with Rayleigh scattering, aerosol and ozone, and single scattering with SKYCOLOR's correction for multiple scattering. The spectrum goes to XYZ with the color matching fit of Wyman, Sloan and Shirley (2013), and then to linear RGB.

**The scenes do not use it.** It is a tool to understand and compare. `tools/compare_photos.py` measures it against points taken from photos.

## Results

Against 33 points from photos of one evening, as distance in CIE u'v':

| Measure | Error |
|---|---|
| Model, mean | 0.019 |
| A neutral gray, as a reference | 0.032 |
| Blue sky, high points | 0.004 to 0.010 |
| Pink band opposite the Sun | 0.025 to 0.027: the model makes it too yellow |
| Gold band next to the Sun | 0.032 |

## What it taught

- **Do not copy its colors into the tables.** A real sky is very pale: averaged, it is almost white. On LEDs that looks wrong, so the tables in `settings.toml` are set by hand and more saturated.
- **A clear sky hardly turns red.** The horizon stays orange and the rest turns lilac. Red and pink come from clouds.
- **The color of a cloud can be predicted** with data that already arrives, see [clouds.md](clouds.md).
- **The air decides how vivid an evening is,** and clean air is what looks vivid, see [atmosphere.md](atmosphere.md).
- **A formula gives the light, not the bytes.** The step to LEDs is its own problem, see [led-color.md](led-color.md).

## Use it elsewhere

```python
from luces.physics.sky_model import Atmosphere, to_hex
a = Atmosphere()
rgb, luminance = a.to_rgb(a.sky_spectrum(sun_altitude=-1, elevation=20, azimuth=150))
print(to_hex(rgb))
```

`azimuth` is measured from the Sun: 0 looks towards it, 180 away from it.

## Limits

- 33 points of a single evening, picked by eye, from photos a phone processed.
- The fit preferred an aerosol depth of 0.03, which is not believable, and barely changes the error: it does not measure real aerosol.
- The share of direct light on clouds (2 %) is an estimate.

## Sources

- [Sky Dome Appearance Project: Hosek-Wilkie and Prague](https://cgg.mff.cuni.cz/projects/SkylightModelling/)
- [Zotti and others, 2007: critique of the Preetham model](https://www.cg.tuwien.ac.at/research/publications/2007/zotti-2007-wscg/zotti-2007-wscg-paper.pdf)
- [Lange, Rozanov and von Savigny, 2023: why is the sky blue?](https://acp.copernicus.org/articles/23/14829/2023/)
- [Gedzelman: SKYCOLOR](https://ams.confex.com/ams/pdfpapers/119065.pdf)
- [Bruneton: Precomputed Atmospheric Scattering](https://github.com/ebruneton/precomputed_atmospheric_scattering)

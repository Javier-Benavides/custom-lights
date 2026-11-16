# Licenses and credits

Everything here is under the [MIT license](LICENSE), with one exception.

| File | License | Why |
|---|---|---|
| `luces/hardware/ite.py` | [GPL-2.0-or-later](LICENSES/GPL-2.0-or-later.txt) | Written from reading OpenRGB's `GigabyteRGBFusion2USBController` |
| Everything else | MIT | |

`luces/physics/` does not import `ite.py`, so it can be reused under the MIT license alone. Anyone distributing the whole program, including `ite.py`, must follow the GPL for that file.

This is not legal advice.

## Credits

- [OpenRGB](https://gitlab.com/CalcProgrammer1/OpenRGB): the protocol of the ITE IT5711 chip.
- [Eric Bruneton, Precomputed Atmospheric Scattering](https://github.com/ebruneton/precomputed_atmospheric_scattering): the solar spectrum and ozone cross section tables in `luces/physics/sky_model.py`, under the BSD 3-Clause license. Copyright (c) 2017 Eric Bruneton.
- NOAA's formulas for the position of the Sun, based on Jean Meeus, *Astronomical Algorithms*.
- Wyman, Sloan and Shirley (2013): the fit of the color matching functions.
- [FastLED](https://github.com/FastLED/FastLED): the idea of one heat deciding a fire's color, from Fire2012. No code was taken.

Data from NOAA and NASA, see [docs/data-sources.md](docs/data-sources.md).

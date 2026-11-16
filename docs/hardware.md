# Hardware

## What is supported

One controller today: the **ITE IT5711** (USB `048d:5711`) on Gigabyte boards, used through `hidraw` in direct mode. Tested on one board, a Gigabyte X870E AERO X3D WOOD, firmware 1.0.4.13, on Ubuntu, with one set of ARGB fans and a cooler on two headers.

**Use it at your own risk.** The code avoids every command known to write to flash, but it has been tested on one machine only.

## Safety rules

- Colors live in the chip's RAM. Nothing here writes to flash.
- `ALLOWED` in `luces/hardware/ite.py` is a closed list. Never add `0x5E` (save to flash), `0x33` (write calibration) or `0x47` (persistence, unknown).
- The chip is not reached through SMBus, and `acpi_enforce_resources=lax` is never needed.
- `max_brightness` is a limit on current: LED headers have a limit, and the real one for each board varies. 70 % is a conservative default. Assuming 60 mA per LED, a full white on 32 LEDs in each of 4 parallel fans could draw about 1.9 A; with the limit, about 1.3 A.
- ARGB headers are 5 V. Never connect them to a 12 V header.

## LEDs are not a screen

Everything in `settings.toml` was tuned by eye on one set of fans. Expect to retune it.

- **Green washes colors out.** A real orange needs far less green than a screen's: `#FF5A14` reads as full orange and `#FF9628` looks pale.
- **White is not `#FFFFFF`.** To look white, green must sit below red and blue.
- **Below about 25 % brightness colors fall apart.** There are few steps of light left: bytes like `20, 2, 9` look deep purple.
- **At low brightness, round all channels together.** `color.to_bytes` keeps the proportion of the largest channel.
- **LEDs are seen one by one when the fans are still.** Never spread a fraction across LEDs to gain resolution: `(1, 0, 1)`, `(0, 1, 1)` and `(0, 0, 1)` look pink, green and blue on the same fan.
- **Gamma matters.** Scenes work as the eye sees, and `color.to_linear` turns that into light before blending.

## Adding a controller

An output is any object with `start`, `paint`, `close` and `info`, see `luces/hardware/__init__.py`. Read [`luces/hardware/AGENTS.md`](../luces/hardware/AGENTS.md) first. A new controller needs a human with the hardware: no agent can verify it.

## Commands

```bash
luces diagnose
```

```bash
luces test case '#FF5A14'
```

```bash
luces test-chain case
```

They need the service stopped, and either `sudo` or `system/grant-chip-access.sh`.

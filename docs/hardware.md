# Hardware

## What is supported

One controller today: the **ITE IT5711** (USB `048d:5711`) on Gigabyte boards, used through `hidraw` in direct mode. Tested on one board, a Gigabyte X870E AERO X3D WOOD, firmware 1.0.4.13, on Ubuntu, with one set of ARGB fans and a cooler on two headers.

Three devices can follow the color of one zone, each with one model only. They are off by default: turn on the ones you have in `settings.toml`.

| Device | How | Tested |
|---|---|---|
| **Razer Basilisk V3** mouse (USB `1532:0099`) | `hidraw`, vendor interface 3 | Colors and black checked by eye on one mouse |
| **MSI RTX 5070 Ti Gaming Trio** GPU light (PCI `10de:2c05`, subsystem `1462:5315`) | I2C, bus 1 of the NVIDIA card, address `0x68` | Colors and off checked by eye on one card |
| **XPG SORCERER 80B ISO** keyboard (USB `125f:730e`, firmware 1.05) | `hidraw`, configuration interface 2 | One keyboard: colors, the unlock after unplugging it, and the floor of light |

They follow a zone of the board's chip, so today they need the chip working.

**Use it at your own risk.** The code avoids every command known to write to flash, but it has been tested on one machine only.

## Safety rules

- Colors live in the chip's RAM. Nothing here writes to flash.
- `ALLOWED` in `luces/hardware/ite.py` is a closed list. Never add `0x5E` (save to flash), `0x33` (write calibration) or `0x47` (persistence, unknown).
- The chip is not reached through SMBus, and `acpi_enforce_resources=lax` is never needed.
- `max_brightness` is a limit on current: LED headers have a limit, and the real one for each board varies. 70 % is a conservative default. Assuming 60 mA per LED, a full white on 32 LEDs in each of 4 parallel fans could draw about 1.9 A; with the limit, about 1.3 A.
- ARGB headers are 5 V. Never connect them to a 12 V header.
- Each device has its own closed allow-list, tested against the commands that save: see below.

## The mouse

- Only two commands: draw the custom frame, and switch to it **without saving**. The static, wave and spectrum effects and brightness save to the mouse, so they are never sent.
- All 11 LEDs (logo, wheel and bottom strip) get the same color. Unplugging the mouse brings back its stored profile.

## The GPU light

- Only one-byte writes to a few registers, on one bus and one address, checked by name and PCI IDs. The bus is never scanned or read.
- **Never register `0x3F`: it saves.** A full power-off brings back the card's stored mode.
- Register `0x36` (brightness) changed nothing on the tested card, so brightness goes in the color. The registers read zero, so the service sends the color again every minute.
- It needs the `i2c-dev` kernel module: `sudo modprobe i2c-dev`, or a line in `/etc/modules-load.d/`.
- It changes at most every `interval_s`, to the average color of that time: a color is 7 writes, about 140 ms.

## The keyboard

- The service draws the per-key canvas, which is never saved, every 40 ms. With no frames, the keyboard goes back to its stored effect.
- **It locks each time it is plugged in:** it takes commands but neither redraws nor saves. The service sees this (a locked keyboard answers each frame with a report) and sends the unlock its vendor's software sends at start: 13 commands, about 9 s. The last command saves the fallback effect, a rainbow, once. So there is at most one unlock a minute and 48 a day.
- Never `0xA0`, `0xA1`, `0xA4` or `0xA5` (info, profile state, key map, macros). Profile changes and saves go only in the 13 exact packets of the unlock.
- **Privacy:** interface 2 also carries a report with the keys being pressed. The service only counts those reports and never reads them, and it has no network. `system/install.sh` grants access to that interface only if `[keyboard]` is enabled: turn it on, then run the installer again.
- `floor` keeps a little light on the keys at night or with the scene off. Above the floor nothing changes.

## LEDs are not a screen

Everything in `settings.toml` was tuned by eye on one set of fans. Expect to retune it.

- **Green washes colors out.** A real orange needs far less green than a screen's: `#FF5A14` reads as full orange and `#FF9628` looks pale.
- **White is not `#FFFFFF`.** To look white, green must sit below red and blue.
- **Below about 25 % brightness colors fall apart.** There are few steps of light left: bytes like `20, 2, 9` look deep purple.
- **At low brightness, round all channels together.** `color.to_bytes` keeps the proportion of the largest channel.
- **LEDs are seen one by one when the fans are still.** Never spread a fraction across LEDs to gain resolution: `(1, 0, 1)`, `(0, 1, 1)` and `(0, 0, 1)` look pink, green and blue on the same fan.
- **Gamma matters.** Scenes work as the eye sees, and `color.to_linear` turns that into light before blending.

## Adding a controller

An output is any object with `start`, `paint`, `close` and `info`, and a device needs only `show` and `close`: see `luces/hardware/__init__.py`. Read [`luces/hardware/AGENTS.md`](../luces/hardware/AGENTS.md) first. A new controller or device needs a human with the hardware: no agent can verify it.

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

# Instructions for this folder

**This code talks to real hardware. A wrong command can damage a board.** Read `AGENTS.md` at the root first.

This is a protected path: change it only if the maintainer's spec names it.

## Rules

- Never add `0x5E`, `0x33` or `0x47` to `ALLOWED` in `ite.py`. They write to flash or may do so.
- `razer.py`: only the custom frame (`0x0F 0x03`) and its mode without saving (`0x0F 0x02` with `00 00 08`). Never the static, wave or spectrum effects, nor brightness: they save to the mouse (VARSTORE).
- `msi_gpu.py`: never register `0x3F`, which saves. Never scan or read the I2C bus, and never use another bus or address.
- `xpg_sorcerer.py`: never `0xA0`, `0xA1`, `0xA4` or `0xA5`. `0xA6`, `0xEA` and any effect other than the canvas go only in the 13 exact packets of `UNLOCK`. Report 5 on interface 2 carries the keys being pressed: count it, never read or keep its content.
- Every packet goes through `_send` (or `_write` for the GPU), which checks the allow-list. Never write to a device any other way.
- A new command must be proven harmless, from a public reference, and reviewed by a person with the hardware.
- Tests here use a fake chip. They cannot prove a command is safe.
- `ite.py`, `razer.py` and `msi_gpu.py` are under GPL-2.0-or-later. Keep their headers. New code derived from OpenRGB or OpenRazer must carry the same license, and a row in `NOTICE.md`.
- `xpg_sorcerer.py` holds only facts of the protocol. Never paste code or text from the vendor's software.

## An output

`service.py` needs only this:

```python
class MyOutput:
    info = {"firmware": "1.0"}
    def start(self, leds_by_header): ...
    def paint(self, colors_by_header): ...   # {header: [(r, g, b), …]} in bytes
    def close(self): ...
```

It raises `OSError` if the device goes away, and the service retries.

## A device

A mouse, a GPU light or a keyboard follows one zone in one color. `luces/emitter.py` drives it from its own thread and needs only this:

```python
class MyDevice:
    def __init__(self): ...        # finds and opens it; raises OSError if it is not there
    def show(self, rgb): ...       # the whole device in one color, in bytes; (0, 0, 0) is off
    def close(self): ...
```

Add it to `DEVICES` in `luces/service.py` and in `luces/settings.py`, with its settings in `settings.toml`, off by default.

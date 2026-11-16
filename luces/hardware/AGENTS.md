# Instructions for this folder

**This code talks to real hardware. A wrong command can damage a board.** Read `AGENTS.md` at the root first.

This is a protected path: change it only if the maintainer's spec names it.

## Rules

- Never add `0x5E`, `0x33` or `0x47` to `ALLOWED` in `ite.py`. They write to flash or may do so.
- Every packet goes through `_send`, which checks the allow-list. Never write to the device any other way.
- A new command must be proven harmless, from a public reference, and reviewed by a person with the hardware.
- Tests here use a fake chip. They cannot prove a command is safe.
- `ite.py` is under GPL-2.0-or-later. Keep its header. New code derived from OpenRGB must carry the same license.

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

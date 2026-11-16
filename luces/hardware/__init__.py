"""Outputs: the code that talks to real LEDs.

An output is any object with `start(leds_by_header)`, `paint(colors_by_header)`, `close()` and an `info` dict, where
colors are lists of (r, g, b) bytes. `luces/service.py` only uses that, so a new controller is one new module here.
Read luces/hardware/AGENTS.md before changing anything in this folder: a wrong command can damage a board.
"""

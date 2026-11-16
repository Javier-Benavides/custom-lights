"""Models of light and motion. This package is the part meant to be reused.

Rules, enforced by tests/test_architecture.py:

- Only the standard library and other modules of this package may be imported.
- No clock, files, network or global state: the same arguments always give the same result.
- Time is seconds, angles are degrees, colors are (r, g, b) tuples from 0 to 1.

A *pattern* is a frozen dataclass that is called with a time and returns a number:

    from luces.physics.fire import Tongues
    tongues = Tongues(every_s=0.6)
    level = tongues(time.time())

The theory, sources and limits of each module are in docs/physics/.
"""

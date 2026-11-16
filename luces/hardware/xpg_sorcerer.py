"""The XPG SORCERER 80B ISO keyboard (USB 125f:730e): its lighting protocol, the bytes and timings on the USB bus.

Tested on one keyboard, with firmware 1.05. Everything goes through configuration report 0x07 on USB interface 2:
264 bytes, the report number and 263 bytes of data, sent with HIDIOCSFEATURE as they are (byte 0 = 0x07, byte 1 = the
command).

What matters:
- The service draws a per-key canvas (effect 8), which is never saved: the vendor's software sends one frame every
  40 ms in its sync mode. When frames stop, the keyboard goes back to its stored effect.
- **The start-up lock.** Each time the keyboard is plugged in, it accepts commands but neither redraws nor saves. The
  vendor's software frees it at start: it walks the 5 profiles with 0xA6 + 0xEA, and ends with 0xA6 0, an effect and
  0xEA. These 13 commands, with the timings seen on the bus, are `UNLOCK`. Only the last 0xEA really saves (the
  others arrive while locked): it stores the fallback effect, a rainbow, which the keyboard shows when nobody sends it
  a canvas. It saves once per unlock, so unlocks are limited: one a minute and 48 a day.
- A locked keyboard answers each canvas page with a report 5; a free one does not. That is how a lock is detected.
- `packet` lets through reads, the canvas and, only inside the unlock, its 13 exact packets. Never 0xA0, 0xA1, 0xA4
  or 0xA5, and never another 0xA6, 0xEA or effect.

Privacy: interface 2 also carries report 5, whose bytes 8 to 23 are the keys being pressed. Here those reports are
only counted. Their content is never looked at or kept.
"""
import fcntl
import glob
import os
import sys
import time

VID, PID = 0x125F, 0x730E
INTERFACE = 2
REPORT = 0x07
SIZE = 264
CELLS = 128                 # the canvas: 2 pages of 256 bytes, 4 bytes per LED cell
PAGE_PAUSE_S = 0.005        # the vendor's software waits 5 ms after each page
STATUS = 0x05               # the report the keyboard sends by itself when something changes

# Commands (byte 1 of the packet): 0xB_ reads, 0xA_ writes.
READ_PROFILE_STATE = 0xB1
READ_EFFECT = 0xB3
READ_KEYS = 0xB4
READ_MACROS = 0xB5
READ_ACTIVE_PROFILE = 0xB6
SET_INFO = 0xA0             # includes the keyboard lock and lights off
SET_PROFILE_STATE = 0xA1
SET_EFFECT = 0xA3           # byte 2 effect, 3 direction, 4 speed, 5 brightness (0 to 100), colors from byte 6
SET_KEYS = 0xA4             # the key map
SET_MACRO = 0xA5
CHANGE_PROFILE = 0xA6       # byte 7 = profile
SAVE = 0xEA                 # stores the profile of byte 2 in the keyboard's memory

EFFECTS = {0: "static", 1: "breathing", 2: "reactive", 3: "ripple", 4: "color cycle", 5: "rainbow", 6: "random",
           7: "comet", 8: "canvas", 9: "starlight", 10: "rising wave"}
CANVAS = 8
ALLOWED = frozenset({READ_PROFILE_STATE, READ_EFFECT, READ_ACTIVE_PROFILE, SET_EFFECT, CHANGE_PROFILE, SAVE})
NEVER = frozenset({SET_INFO, SET_PROFILE_STATE, SET_KEYS, SET_MACRO})

# The unlock: (ms from the first packet, bytes from byte 1). The same packets and timings as the vendor's software at
# start. It was not tried faster.
UNLOCK = (
    (0, "a6"), (1634, "ea"),
    (1742, "a6000000000001"), (3346, "ea01"),
    (3447, "a6000000000002"), (5072, "ea02"),
    (5174, "a6000000000003"), (6828, "ea03"),
    (6930, "a6000000000004"), (8530, "ea04"),
    (8632, "a6"), (8641, "a305014b640000ff"), (8648, "ea"),      # last step: profile 0, rainbow fallback, save
)
NOTICE_WAIT_S = 0.05        # when locked, each page brings a report 5 within 5 to 20 ms (more behind a hub)
BETWEEN_UNLOCKS_S = 60.0    # each unlock saves once in the keyboard's memory: never two in a row
UNLOCKS_A_DAY = 48          # nor more than this in 24 hours: a KVM switch plugs the keyboard in again at every switch
NOTICES_IN_A_ROW = 50       # frames in a row with a report 5 (2 s): it locked again without being unplugged
_unlocks = []               # times (monotonic) of the unlocks of this run


class Forbidden(ValueError):
    """A packet outside the allow-list."""


class Locked(OSError):
    """The keyboard is still locked, and it is not time to unlock it yet."""


def _build(data):
    data = bytes(data)
    if len(data) > SIZE - 1:
        raise Forbidden("packet too long")
    p = bytearray(SIZE)
    p[0] = REPORT
    p[1:1 + len(data)] = data
    return bytes(p)


UNLOCK_PACKETS = frozenset(_build(bytes.fromhex(hx)) for _, hx in UNLOCK)


def packet(data, unlock=False):
    """Builds and checks a 264-byte packet. Reads and the canvas pass; with `unlock`, also the 13 exact packets of the
    unlock, and no other 0xA6, 0xEA or effect."""
    p = _build(data)
    command = p[1]
    if command not in ALLOWED:
        raise Forbidden("command 0x%02X is not on the allow-list" % command)
    if command in (CHANGE_PROFILE, SAVE) or (command == SET_EFFECT and p[2] != CANVAS):
        if unlock and p in UNLOCK_PACKETS:
            return p
        raise Forbidden("0x%02X only with the exact bytes of the unlock" % command)
    if command == SET_EFFECT and (p[3] != 0 or p[4] not in (0, 1) or p[5] != 0):
        raise Forbidden("0xA3 only as a temporary canvas")
    return p


def frame(colors):
    """The 2 packets of one canvas frame. `colors`: one (r, g, b) for every cell, or a list of up to 128.
    A black cell is all zeros, and a lit one has 0x64 in front, as the vendor's software sends them."""
    if isinstance(colors, tuple):
        colors = [colors] * CELLS
    data = bytearray(4 * CELLS)
    for i, (r, g, b) in enumerate(colors[:CELLS]):
        data[4 * i:4 * i + 4] = bytes([0x64 if (r or g or b) else 0, r, g, b])
    return [packet(bytes([SET_EFFECT, CANVAS, 0, page, 0]) + bytes(data[256 * page:256 * (page + 1)])) for page in (0, 1)]


def ioc(number, size):
    return (3 << 30) | (size << 16) | (ord("H") << 8) | number


HIDIOCSFEATURE = ioc(0x06, SIZE)


def find(root="/sys/class/hidraw"):
    """The node of interface 2. Found by identity: the hidraw number changes when the keyboard is plugged in again."""
    mark = "0003:0000%04X:0000%04X" % (VID, PID)
    for folder in sorted(glob.glob(os.path.join(root, "hidraw*"))):
        try:
            with open(os.path.join(folder, "device", "uevent"), encoding="utf-8") as f:
                if mark not in f.read().upper():
                    continue
            interface = os.path.dirname(os.path.realpath(os.path.join(folder, "device")))
            with open(os.path.join(interface, "bInterfaceNumber"), encoding="ascii") as f:
                if int(f.read().strip(), 16) != INTERFACE:
                    continue
        except (OSError, ValueError):
            continue
        return "/dev/" + os.path.basename(folder)
    return None


class KeyboardLights:
    """The keyboard for the service (`luces/emitter.py`). On opening it checks whether the keyboard is locked and, if so,
    unlocks it. After that each color is one canvas frame, which is never saved; the emitter repeats it every
    `refresh_s`."""

    def __init__(self, path=None, ioctl=fcntl.ioctl, read=os.read, sleep=time.sleep, clock=time.monotonic,
                 open_=os.open, close=os.close):
        self.path = path or find()
        if not self.path:
            raise FileNotFoundError("XPG SORCERER keyboard 125f:730e not found")
        self._ioctl, self._read, self._sleep, self._clock, self._close = ioctl, read, sleep, clock, close
        self._in_a_row = 0
        self.unlocked = False
        self.fd = open_(self.path, os.O_RDWR | os.O_NONBLOCK)
        try:
            if self.locked():
                self.unlock()
                if self.locked():
                    raise Locked("the keyboard is still locked after the unlock")
        except BaseException:
            self.close()
            raise

    def _send(self, p, unlock=False):
        """Every packet goes through here, and through the allow-list again."""
        if packet(p[1:], unlock) != p:
            raise Forbidden("unchecked packet")
        self._ioctl(self.fd, HIDIOCSFEATURE, p)

    def _notices(self):
        """How many reports 5 arrived since last time. They are only counted: bytes 8 to 23 are keys."""
        n = 0
        while True:
            try:
                d = self._read(self.fd, 64)
            except BlockingIOError:
                return n
            if len(d) >= 28 and d[0] == STATUS:
                n += 1

    def _frame(self, rgb):
        for p in frame(tuple(rgb)):
            self._send(p)
            self._sleep(PAGE_PAUSE_S)

    def locked(self):
        """Two black frames: one with no report 5 is enough to know it is free (a pressed key can add a report, never
        take one away)."""
        self._notices()
        for _ in range(2):
            self._frame((0, 0, 0))
            self._sleep(NOTICE_WAIT_S)
            if not self._notices():
                return False
        return True

    def unlock(self):
        now = self._clock()
        del _unlocks[:-UNLOCKS_A_DAY]
        if _unlocks and now - _unlocks[-1] < BETWEEN_UNLOCKS_S:
            raise Locked("keyboard locked; the last unlock was less than %d s ago" % BETWEEN_UNLOCKS_S)
        if len(_unlocks) >= UNLOCKS_A_DAY and now - _unlocks[0] < 86400:
            raise Locked("keyboard locked; there were already %d unlocks in 24 hours" % UNLOCKS_A_DAY)
        _unlocks.append(now)
        print("keyboard: locked after being plugged in; sending the unlock (13 commands, about 9 s)", file=sys.stderr)
        start = self._clock()
        for ms, hx in UNLOCK:
            self._sleep(max(0.0, start + ms / 1000 - self._clock()))
            self._send(_build(bytes.fromhex(hx)), unlock=True)
        self._sleep(0.3)
        self.unlocked = True

    def show(self, rgb):
        """The whole keyboard in one color, in bytes. (0, 0, 0) is black. If frames bring reports 5 again for 2 s, the
        keyboard locked again: it is released, and opening it again unlocks it."""
        self._in_a_row = self._in_a_row + 1 if self._notices() else 0
        if self._in_a_row >= NOTICES_IN_A_ROW:
            raise Locked("the keyboard locked again")
        self._frame(rgb)

    def close(self):
        if self.fd is not None:
            self._close(self.fd)
            self.fd = None

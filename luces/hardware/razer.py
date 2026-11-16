# SPDX-License-Identifier: GPL-2.0-or-later
# Written from reading OpenRazer's driver/razerchromacommon.c, which is under the GPL.
# See NOTICE.md. The rest of this project is under the MIT license.
"""The Razer Basilisk V3 mouse (USB 1532:0099), through hidraw on its vendor interface (number 3).

What matters:
- 90-byte Feature reports, sent with a 0x00 in front because the interface uses no report ID. Transaction ID 0x1F.
- Byte 88 is the XOR of bytes 2 to 87.
- Only two commands, and neither one saves: draw the row of the custom frame (0x0F 0x03), and switch to the custom
  frame without saving (0x0F 0x02, arguments 00 00 08). Unplugging the mouse brings back its stored profile.
- `allow` refuses everything else. Never the static, wave or spectrum effects, nor brightness: they use VARSTORE and
  stay saved in the mouse.
"""
import fcntl
import glob
import os
import time

HID_ID = "0003:00001532:00000099"
INTERFACE = "03"
SIZE = 90
TRANSACTION = 0x1F
LEDS = 11                                   # one row of 11: logo, wheel and the strip underneath
FRAME = (0x0F, 0x03)
MODE = (0x0F, 0x02)
FRAME_SIZE = 0x47
MODE_SIZE = 0x0C
MODE_ARGS = bytes((0x00, 0x00, 0x08))       # do not save (0x00), every LED (0x00), custom frame effect (0x08)
WAIT_S = 0.01        # between sending and reading the answer. OpenRazer waits 1 ms; 80 ms also worked
STATUS = {0x00: "new", 0x01: "busy", 0x02: "ok", 0x03: "failed", 0x04: "no answer", 0x05: "not supported"}


class NoMouse(OSError):
    pass


def _ioc_hid(number, size):
    return (3 << 30) | (size << 16) | (ord("H") << 8) | number   # _IOC(_IOC_READ|_IOC_WRITE, 'H', n, size)


HIDIOCSFEATURE = _ioc_hid(0x06, SIZE + 1)
HIDIOCGFEATURE = _ioc_hid(0x07, SIZE + 1)
ALLOWED = frozenset({FRAME, MODE})


def find(root="/sys/class/hidraw"):
    """The node of interface 3. Found by identity: the hidraw number changes when the mouse is plugged in again."""
    for folder in sorted(glob.glob(os.path.join(root, "hidraw*"))):
        try:
            with open(os.path.join(folder, "device", "uevent"), encoding="utf-8") as f:
                if HID_ID not in f.read().upper():
                    continue
            interface = os.path.dirname(os.path.realpath(os.path.join(folder, "device")))
            with open(os.path.join(interface, "bInterfaceNumber"), encoding="ascii") as f:
                if f.read().strip() != INTERFACE:
                    continue
        except OSError:
            continue
        return "/dev/" + os.path.basename(folder)
    return None


def allow(command_class, command, arguments):
    """The allow-list: the whole of row 0 of the frame, or the frame mode without saving. Nothing else."""
    arguments = bytes(arguments)
    if (command_class, command) == FRAME:
        ok = len(arguments) == 5 + 3 * LEDS and arguments[:5] == bytes((0, 0, 0, 0, LEDS - 1))
    elif (command_class, command) == MODE:
        ok = arguments == MODE_ARGS
    else:
        ok = False
    if not ok:
        raise ValueError(f"mouse command not allowed: {command_class:#04x} {command:#04x} {arguments[:5].hex(' ')}")


def packet(command_class, command, size, arguments):
    allow(command_class, command, arguments)
    r = bytearray(SIZE)
    r[1], r[5], r[6], r[7] = TRANSACTION, size, command_class, command
    r[8:8 + len(arguments)] = arguments
    crc = 0
    for b in r[2:88]:
        crc ^= b
    r[88] = crc
    return bytes(r)


def frame_packet(rgb):
    return packet(*FRAME, FRAME_SIZE, bytes((0, 0, 0, 0, LEDS - 1)) + bytes(rgb) * LEDS)


def mode_packet():
    return packet(*MODE, MODE_SIZE, MODE_ARGS)


class Mouse:
    def __init__(self, path=None, ioctl=fcntl.ioctl, sleep=time.sleep, open_=os.open, close=os.close):
        self.path = path or find()
        if self.path is None:
            raise NoMouse("Razer mouse 1532:0099 not found")
        self._ioctl, self._sleep, self._close = ioctl, sleep, close
        self._fd = open_(self.path, os.O_RDWR)

    def close(self):
        if self._fd is not None:
            self._close(self._fd)
            self._fd = None

    def _answer(self):
        buffer = bytearray(SIZE + 1)
        self._ioctl(self._fd, HIDIOCGFEATURE, buffer, True)
        return buffer[1]

    def _send(self, p):
        """Every packet goes through here, and through the allow-list again."""
        if len(p) != SIZE or p[1] != TRANSACTION:
            raise ValueError("badly built mouse packet")
        allow(p[6], p[7], p[8:8 + (5 + 3 * LEDS if (p[6], p[7]) == FRAME else len(MODE_ARGS))])
        self._ioctl(self._fd, HIDIOCSFEATURE, bytearray(b"\0" + p), True)
        self._sleep(WAIT_S)
        status = self._answer()
        if status in (0x00, 0x01):                  # not done yet: it gets a little longer, once
            self._sleep(0.03)
            status = self._answer()
        if status in (0x03, 0x05):
            raise OSError(f"the mouse answered '{STATUS[status]}'")
        return STATUS.get(status, hex(status))

    def show(self, rgb):
        """The whole mouse in one color, in bytes. (0, 0, 0) is black."""
        self._send(frame_packet(rgb))
        self._send(mode_packet())

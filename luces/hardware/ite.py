# SPDX-License-Identifier: GPL-2.0-or-later
# Written from reading OpenRGB's Controllers/GigabyteRGBFusion2USBController, which is under the GPL.
# See NOTICE.md. The rest of this project is under the MIT license.
"""The lighting chip on the board (ITE IT5711, USB 048d:5711), through hidraw.

Protocol taken from the code of OpenRGB 1.1, which drives this board with the it5711_11_device layout. Only what direct
mode needs is used.

What matters:
- Everything goes in 64-byte Feature reports with ID 0xCC, through the vendor interface (0xFF89/0xCC).
- Colors live in the chip's RAM. Nothing here writes to flash.
- `_send` only lets through the commands in ALLOWED. Never 0x5E (save to flash), 0x33 (write calibration) or
  0x47 (persistence: it is unknown whether it writes).
"""
import fcntl
import glob
import os
import struct
import time

HID_ID = "0003:0000048D:00005711"
REPORT_ID = 0xCC
REPORT_SIZE = 64
LEDS_PER_PACKET = 19
HEADERS = {1: 0x58, 2: 0x59, 3: 0x62}    # HDR_D_LEDn_ARGB: where the colors of each header go
EFFECTS_OFF = 0x7B                       # every header in direct mode, with no chip effect
ALLOWED = frozenset({0x28, 0x31, 0x32, 0x34, 0x48, 0x60, 0x61, *range(0x20, 0x28), *range(0x90, 0x93), *HEADERS.values()})
DEFAULT_ORDER = (1, 0, 2)                # GRB, the usual order in addressable LEDs


class NoController(OSError):
    pass


def _ioc_hid(number, size):
    return (3 << 30) | (size << 16) | (ord("H") << 8) | number   # _IOC(_IOC_READ|_IOC_WRITE, 'H', n, size)


HIDIOCSFEATURE = _ioc_hid(0x06, REPORT_SIZE)
HIDIOCGFEATURE = _ioc_hid(0x07, REPORT_SIZE)


def find(root="/sys/class/hidraw"):
    """The node of interface 0xFF89/0xCC. Searched by identity: the hidraw number and the USB path change."""
    for folder in sorted(glob.glob(os.path.join(root, "hidraw*"))):
        try:
            with open(os.path.join(folder, "device", "uevent"), encoding="utf-8") as f:
                if HID_ID not in f.read().upper():
                    continue
            with open(os.path.join(folder, "device", "report_descriptor"), "rb") as f:
                descriptor = f.read()
        except OSError:
            continue
        if b"\x06\x89\xff" in descriptor and b"\x09\xcc" in descriptor:
            return "/dev/" + os.path.basename(folder)
    return None


def order_from_calibration(value):
    """(r, g, b): the position of each channel. The low byte is blue's; then green and red."""
    order = ((value >> 16) & 0xFF, (value >> 8) & 0xFF, value & 0xFF)
    return order if sorted(order) == [0, 1, 2] else None


class Controller:
    def __init__(self, path=None, ioctl=fcntl.ioctl, sleep=time.sleep, open_=os.open, close=os.close):
        self.path = path or find()
        if self.path is None:
            raise NoController("ITE 048d:5711 controller not found")
        self._ioctl, self._sleep, self._close = ioctl, sleep, close
        self._fd = open_(self.path, os.O_RDWR)
        self.info = {}
        self.order = {}

    def close(self):
        if self._fd is not None:
            self._close(self._fd)
            self._fd = None

    def _send(self, packet):
        if len(packet) != REPORT_SIZE or packet[0] != REPORT_ID or packet[1] not in ALLOWED:
            raise ValueError(f"packet not allowed: {bytes(packet[:4]).hex()}")
        self._ioctl(self._fd, HIDIOCSFEATURE, bytearray(packet), True)

    def _command(self, *data):
        self._send(bytes((REPORT_ID, *data)).ljust(REPORT_SIZE, b"\0"))

    def _request(self, command):
        self._command(command, 0, 0)
        buffer = bytearray(REPORT_SIZE)
        buffer[0] = REPORT_ID
        self._ioctl(self._fd, HIDIOCGFEATURE, buffer, True)
        return bytes(buffer)

    def read_info(self):
        """Read only: the identity and calibration stored in the chip."""
        r = self._request(0x60)
        c = self._request(0x61)
        calibration = list(struct.unpack_from("<2I", r, 44)) + list(struct.unpack_from("<4I", c, 4))
        self.info = {
            "product": r[1], "device": r[2], "strips_detected": r[3],
            "firmware": ".".join(str(b) for b in r[4:8]), "support": r[11],
            "name": r[12:40].split(b"\0")[0].decode("ascii", "replace"),
            "chip": struct.unpack_from("<I", r, 56)[0], "calibration": calibration,
        }
        self.order = {h: order_from_calibration(calibration[h - 1]) or DEFAULT_ORDER for h in HEADERS}
        return self.info

    def start(self, leds_by_header):
        """The same as OpenRGB at startup: clears the chip's effects and leaves the headers in direct mode."""
        self.read_info()
        if self.info["support"] & 0x02:
            self._command(0x48, 0, 0)                 # turns LampArray mode off
        for register in (*range(0x20, 0x28), *range(0x90, 0x93)):
            self._command(register, 0, 0)
        self._command(0x28, 0xFF, 0x07)
        self._command(0x31, 0, 0)
        self._set_led_counts(leds_by_header)
        self._command(0x32, EFFECTS_OFF, 0)
        self._sleep(0.05)

    def _set_led_counts(self, leds_by_header):
        def size_code(n):
            for code, limit in enumerate((32, 64, 256, 512)):
                if n <= limit:
                    return code
            return 4

        n = [size_code(leds_by_header.get(h, 0)) for h in (1, 2, 3)]
        self._command(0x34, (n[1] << 4) | n[0], n[2], 0)
        self._sleep(0.02)

    def paint(self, colors_by_header):
        """One frame: {header: [(r, g, b), …]} in bytes. The headers change within milliseconds of each other."""
        for header, colors in colors_by_header.items():
            order = self.order.get(header, DEFAULT_ORDER)
            for first in range(0, len(colors), LEDS_PER_PACKET):
                chunk = colors[first:first + LEDS_PER_PACKET]
                packet = bytearray(REPORT_SIZE)
                packet[0], packet[1] = REPORT_ID, HEADERS[header]
                struct.pack_into("<H", packet, 2, first * 3)
                packet[4] = len(chunk) * 3
                for i, led in enumerate(chunk):
                    for channel in range(3):
                        packet[5 + i * 3 + order[channel]] = led[channel]
                self._send(packet)
        self._command(0x28)

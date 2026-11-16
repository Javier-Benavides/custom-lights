# SPDX-License-Identifier: GPL-2.0-or-later
# Written from reading OpenRGB's Controllers/MSIGPUController (MSIGPUv2), which is under the GPL.
# See NOTICE.md. The rest of this project is under the MIT license.
"""The light of the MSI RTX 5070 Ti Gaming Trio OC (10de:2c05, subsystem 1462:5315), through I2C.

What matters:
- Only the bus "NVIDIA i2c adapter 1 at 1:00.0", and only if the card is this one. Only address 0x68.
  The bus is never scanned or read: only one-byte SMBus writes.
- A color: 0x2E<-0, mode 0x22<-0x1C, red 0x30, green 0x31, blue 0x32, brightness 0x36<-100 and mode 0x22<-0x13
  (static), with 20 ms between writes. Off: 0x2E<-0, 0x22<-0x1C, 0x22<-0x01.
- Register 0x36 changed nothing on the tested card: brightness goes in the color. The registers read zero, so there is
  no way to know what the card shows: the service sends it again now and then.
- `allow` lets through only those registers and values. **Never 0x3F: it saves.** A full power-off brings back the
  card's stored mode.
"""
import ctypes
import fcntl
import glob
import os
import time

BUS_NAME = "NVIDIA i2c adapter 1 at 1:00.0"
PCI = (("vendor", "0x10de"), ("device", "0x2c05"), ("subsystem_vendor", "0x1462"), ("subsystem_device", "0x5315"))
ADDRESS = 0x68
PAUSE_S = 0.02
BRIGHTNESS = 100

I2C_SLAVE, I2C_SMBUS = 0x0703, 0x0720
SMBUS_WRITE, SMBUS_BYTE_DATA = 0, 2

MODE, UNKNOWN, RED, GREEN, BLUE, BRIGHTNESS_REGISTER = 0x22, 0x2E, 0x30, 0x31, 0x32, 0x36
OFF, STATIC, IDLE = 0x01, 0x13, 0x1C
ALLOWED = {UNKNOWN: frozenset({0x00}), MODE: frozenset({OFF, STATIC, IDLE}),
           RED: None, GREEN: None, BLUE: None, BRIGHTNESS_REGISTER: frozenset({BRIGHTNESS})}


class NoGpu(OSError):
    pass


class _Data(ctypes.Union):
    _fields_ = [("byte", ctypes.c_uint8), ("word", ctypes.c_uint16), ("block", ctypes.c_uint8 * 34)]


class _Request(ctypes.Structure):                     # struct i2c_smbus_ioctl_data
    _fields_ = [("read_write", ctypes.c_uint8), ("command", ctypes.c_uint8),
                ("size", ctypes.c_uint32), ("data", ctypes.POINTER(_Data))]


def allow(register, value):
    if register not in ALLOWED or not isinstance(value, int) or not 0 <= value <= 255:
        raise ValueError(f"GPU register not allowed: {register:#04x}")
    if ALLOWED[register] is not None and value not in ALLOWED[register]:
        raise ValueError(f"value not allowed in GPU register {register:#04x}: {value:#04x}")


def color_sequence(rgb):
    r, g, b = rgb
    return ((UNKNOWN, 0x00), (MODE, IDLE), (RED, r), (GREEN, g), (BLUE, b), (BRIGHTNESS_REGISTER, BRIGHTNESS), (MODE, STATIC))


def off_sequence():
    return ((UNKNOWN, 0x00), (MODE, IDLE), (MODE, OFF))


def find(root="/sys/bus/i2c/devices"):
    """/dev/i2c-N of the card's bus, by its name and its PCI IDs. Raises NoGpu if it is missing or does not match."""
    for folder in sorted(glob.glob(os.path.join(root, "i2c-*"))):
        try:
            with open(os.path.join(folder, "name"), encoding="utf-8") as f:
                if f.read().strip() != BUS_NAME:
                    continue
            pci = os.path.dirname(os.path.realpath(folder))
            ids = []
            for file, _ in PCI:
                with open(os.path.join(pci, file), encoding="ascii") as f:
                    ids.append((file, f.read().strip().lower()))
        except OSError:
            continue
        if tuple(ids) != PCI:
            raise NoGpu(f"bus {os.path.basename(folder)} is not on the expected card: {dict(ids)}")
        return "/dev/" + os.path.basename(folder)
    raise NoGpu(f"bus '{BUS_NAME}' not found. Is the i2c-dev module loaded?")


class Gpu:
    def __init__(self, path=None, ioctl=fcntl.ioctl, sleep=time.sleep, open_=os.open, close=os.close):
        self.path = path or find()
        self._ioctl, self._sleep, self._close = ioctl, sleep, close
        self._fd = open_(self.path, os.O_RDWR)
        try:
            self._ioctl(self._fd, I2C_SLAVE, ADDRESS)
        except OSError:
            self.close()
            raise

    def close(self):
        if self._fd is not None:
            self._close(self._fd)
            self._fd = None

    def _write(self, register, value):
        """Every write goes through here, and through the allow-list."""
        allow(register, value)
        data = _Data()
        data.byte = value
        self._ioctl(self._fd, I2C_SMBUS, _Request(SMBUS_WRITE, register, SMBUS_BYTE_DATA, ctypes.pointer(data)))
        self._sleep(PAUSE_S)

    def show(self, rgb):
        """A color in bytes. (0, 0, 0) uses the off mode: a black static color might look different on the card."""
        for register, value in (off_sequence() if max(rgb) == 0 else color_sequence(rgb)):
            self._write(register, value)

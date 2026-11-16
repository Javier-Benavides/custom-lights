import os
import tempfile
import unittest

from luces.hardware import msi_gpu

GOLD = (255, 137, 4)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


class FakeBus:
    """Records the I2C writes as (register, value). Any other request fails: the bus is never read or scanned."""

    def __init__(self):
        self.writes, self.addresses, self.pauses = [], [], []

    def ioctl(self, fd, request, arg, *rest):
        if request == msi_gpu.I2C_SLAVE:
            self.addresses.append(arg)
        elif request == msi_gpu.I2C_SMBUS:
            assert arg.read_write == msi_gpu.SMBUS_WRITE and arg.size == msi_gpu.SMBUS_BYTE_DATA
            self.writes.append((arg.command, arg.data.contents.byte))
        else:
            raise AssertionError(f"unexpected ioctl {request:#x}")

    def gpu(self):
        return msi_gpu.Gpu("/dev/fake", ioctl=self.ioctl, sleep=self.pauses.append, open_=lambda p, m: 6, close=lambda fd: None)


class Gpu(unittest.TestCase):
    def test_a_color_byte_by_byte(self):
        bus = FakeBus()
        bus.gpu().show(GOLD)
        self.assertEqual(bus.addresses, [0x68])
        self.assertEqual(bus.writes, [(0x2E, 0x00), (0x22, 0x1C), (0x30, 255), (0x31, 137), (0x32, 4), (0x36, 100), (0x22, 0x13)])
        self.assertEqual(bus.pauses, [0.02] * 7)

    def test_black_is_the_off_mode(self):
        bus = FakeBus()
        bus.gpu().show((0, 0, 0))
        self.assertEqual(bus.writes, [(0x2E, 0x00), (0x22, 0x1C), (0x22, 0x01)])

    def test_never_save_0x3f(self):
        for value in (0x00, 0x01, 0xFF):
            with self.assertRaises(ValueError):
                msi_gpu.allow(0x3F, value)
        bus = FakeBus()
        with self.assertRaises(ValueError):
            bus.gpu()._write(0x3F, 0x01)
        self.assertEqual(bus.writes, [])
        for rgb in ((1, 2, 3), (255, 255, 255), (0, 0, 9)):
            self.assertNotIn(0x3F, [r for r, _ in msi_gpu.color_sequence(rgb)])

    def test_allowed_values(self):
        for register, value in ((0x22, 0x02), (0x22, 0x00), (0x36, 40), (0x2E, 0x01), (0x33, 0x00), (0x30, 256), (0x30, -1)):
            with self.subTest(register=hex(register), value=value):
                with self.assertRaises(ValueError):
                    msi_gpu.allow(register, value)

    def test_finds_the_bus_by_name_and_ids(self):
        with tempfile.TemporaryDirectory() as root:
            def card(pci, ids, bus, name):
                for file, value in zip(("vendor", "device", "subsystem_vendor", "subsystem_device"), ids):
                    write(os.path.join(root, "pci", pci, file), value + "\n")
                write(os.path.join(root, "pci", pci, bus, "name"), name + "\n")
                os.makedirs(os.path.join(root, "buses"), exist_ok=True)
                os.symlink(os.path.join(root, "pci", pci, bus), os.path.join(root, "buses", bus))

            card("0000:00:1f.4", ("0x8086", "0x7a23", "0x1462", "0x7e06"), "i2c-0", "SMBus I801 adapter at efa0")
            card("0000:01:00.0", ("0x10de", "0x2c05", "0x1462", "0x5315"), "i2c-8", msi_gpu.BUS_NAME)
            self.assertEqual(msi_gpu.find(os.path.join(root, "buses")), "/dev/i2c-8")
            write(os.path.join(root, "pci", "0000:01:00.0", "subsystem_device"), "0x5316\n")
            with self.assertRaisesRegex(msi_gpu.NoGpu, "not on the expected card"):
                msi_gpu.find(os.path.join(root, "buses"))
        with tempfile.TemporaryDirectory() as empty:
            with self.assertRaises(msi_gpu.NoGpu):
                msi_gpu.find(empty)


if __name__ == "__main__":
    unittest.main()

import os
import tempfile
import unittest

from luces.hardware import ite

FORBIDDEN = (0x5E, 0x33, 0x47)   # save to flash, write calibration, persistence


class FakeChip:
    """Records what the program sends to the chip, with no hardware."""

    def __init__(self, support=0x02):
        self.sent, self.support = [], support

    def ioctl(self, fd, request, buffer, mutate):
        if request == ite.HIDIOCSFEATURE:
            self.sent.append(bytes(buffer))
        elif request == ite.HIDIOCGFEATURE:
            command = self.sent[-1][1]
            if command == 0x60:
                buffer[1], buffer[3], buffer[11] = 0x01, 0x00, self.support
                buffer[4:8] = bytes((1, 2, 3, 4))
                buffer[12:16] = b"IT57"
                buffer[44:48] = (0x00010002).to_bytes(4, "little")     # header 1: GRB
                buffer[48:52] = (0x00000102).to_bytes(4, "little")     # header 2: RGB
            elif command == 0x61:
                buffer[4:8] = (0).to_bytes(4, "little")                # header 3: no data

    def controller(self):
        return ite.Controller("/dev/fake", ioctl=self.ioctl, sleep=lambda s: None, open_=lambda r, m: 7, close=lambda fd: None)


class Chip(unittest.TestCase):
    def test_startup_follows_openrgb_and_never_touches_flash(self):
        fake = FakeChip()
        fake.controller().start({1: 32, 2: 32})
        commands = [p[1] for p in fake.sent]
        self.assertEqual(commands[:3], [0x60, 0x61, 0x48])
        self.assertEqual(commands[3:14], [*range(0x20, 0x28), 0x90, 0x91, 0x92])
        self.assertEqual(commands[14:], [0x28, 0x31, 0x34, 0x32])
        self.assertEqual(fake.sent[14][:4], bytes((0xCC, 0x28, 0xFF, 0x07)))
        self.assertEqual(fake.sent[-1][:3], bytes((0xCC, 0x32, 0x7B)))
        self.assertTrue(all(len(p) == 64 and p[0] == 0xCC for p in fake.sent))
        self.assertFalse(set(FORBIDDEN) & set(commands))

    def test_no_lamparray_without_support(self):
        fake = FakeChip(support=0)
        fake.controller().start({1: 32})
        self.assertNotIn(0x48, [p[1] for p in fake.sent])

    def test_a_forbidden_command_never_leaves(self):
        fake = FakeChip()
        c = fake.controller()
        for command in FORBIDDEN:
            with self.assertRaises(ValueError):
                c._command(command, 0, 0)
        self.assertEqual(fake.sent, [])

    def test_the_allow_list_has_no_forbidden_command(self):
        self.assertFalse(set(FORBIDDEN) & ite.ALLOWED)

    def test_color_packets(self):
        fake = FakeChip()
        c = fake.controller()
        c.read_info()
        fake.sent.clear()
        c.paint({1: [(10, 20, 30)] * 20, 2: [(10, 20, 30)]})
        p1, p2, p3, apply_ = fake.sent
        self.assertEqual((p1[1], p1[2], p1[3], p1[4]), (0x58, 0, 0, 57))
        self.assertEqual(p1[5:8], bytes((20, 10, 30)))            # GRB
        self.assertEqual((p2[1], p2[2], p2[3], p2[4]), (0x58, 57, 0, 3))
        self.assertEqual(p3[1], 0x59)
        self.assertEqual(p3[5:8], bytes((10, 20, 30)))            # RGB
        self.assertEqual(apply_[:2], bytes((0xCC, 0x28)))
        self.assertEqual(apply_[2:], bytes(62))

    def test_header_3_uses_its_register_and_default_order(self):
        fake = FakeChip()
        c = fake.controller()
        c.read_info()
        self.assertEqual(c.order[3], ite.DEFAULT_ORDER)
        fake.sent.clear()
        c.paint({3: [(1, 2, 3)]})
        self.assertEqual(fake.sent[0][1], 0x62)

    def test_led_counts(self):
        fake = FakeChip()
        fake.controller()._set_led_counts({1: 40, 2: 300, 3: 10})
        self.assertEqual(fake.sent[-1][:5], bytes((0xCC, 0x34, 3 << 4 | 1, 0, 0)))

    def test_finds_the_node_by_identity(self):
        with tempfile.TemporaryDirectory() as root:
            for name, hid, descriptor in (("hidraw0", "0003:0000048D:00005711", b"\x05\x59\x09\x01"),
                                          ("hidraw1", "0003:0000048D:00005711", b"\x06\x89\xff\x09\x10\x09\xcc"),
                                          ("hidraw2", "0003:0000125F:0000730E", b"\x06\x89\xff\x09\xcc")):
                os.makedirs(os.path.join(root, name, "device"))
                with open(os.path.join(root, name, "device", "uevent"), "w") as f:
                    f.write(f"HID_ID={hid}\n")
                with open(os.path.join(root, name, "device", "report_descriptor"), "wb") as f:
                    f.write(descriptor)
            self.assertEqual(ite.find(root), "/dev/hidraw1")

    def test_a_real_descriptor_matches(self):
        real = bytes.fromhex("0689ff0910a101855a0901150026ff0075089510b100c00689ff09cca10185cc0901150026ff007508953fb100c0")
        self.assertIn(b"\x06\x89\xff", real)
        self.assertIn(b"\x09\xcc", real)

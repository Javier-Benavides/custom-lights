import os
import tempfile
import unittest
from unittest import mock

from luces.hardware import razer

GOLD = (255, 137, 4)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


class FakeMouse:
    """Records the reports, and answers 'ok' or what it is told."""

    def __init__(self, answers=None):
        self.sent, self.answers = [], list(answers or [])

    def ioctl(self, fd, request, buffer, mutate):
        if request == razer.HIDIOCSFEATURE:
            self.sent.append(bytes(buffer))
        elif request == razer.HIDIOCGFEATURE:
            buffer[1] = self.answers.pop(0) if self.answers else 0x02

    def mouse(self):
        return razer.Mouse("/dev/fake", ioctl=self.ioctl, sleep=lambda s: None, open_=lambda p, m: 5, close=lambda fd: None)


class Packets(unittest.TestCase):
    def test_frame_byte_by_byte(self):
        expected = bytearray(90)
        expected[1], expected[5], expected[6], expected[7] = 0x1F, 0x47, 0x0F, 0x03
        expected[8:13] = bytes((0, 0, 0, 0, 10))
        expected[13:13 + 33] = bytes(GOLD) * 11
        expected[88] = 0x33        # 47^0F^03^0A ^ FF^89^04 (11 times: one is left)
        self.assertEqual(razer.frame_packet(GOLD), bytes(expected))

    def test_frame_mode_without_saving_byte_by_byte(self):
        p = razer.mode_packet()
        self.assertEqual(p[:11], bytes.fromhex("00 1f 00 00 00 0c 0f 02 00 00 08"))
        self.assertEqual(p[11:88], bytes(77))
        self.assertEqual(p[88:], bytes((0x09, 0x00)))      # 0C^0F^02^08

    def test_xor_of_bytes_2_to_87(self):
        p = razer.frame_packet((12, 200, 77))
        crc = 0
        for b in p[2:88]:
            crc ^= b
        self.assertEqual(p[88], crc)

    def test_the_allow_list_refuses_saving_and_other_effects(self):
        for command_class, command, args in ((0x0F, 0x02, b"\x01\x00\x08"),     # frame mode, saved (VARSTORE)
                                             (0x0F, 0x02, b"\x01\x00\x01"),     # static effect, saved
                                             (0x0F, 0x02, b"\x00\x00\x01"),     # static effect even unsaved
                                             (0x0F, 0x04, b"\x01\x00\xff"),     # brightness
                                             (0x03, 0x03, b"\x01\x05\x01"),     # old LED command
                                             (0x0F, 0x03, bytes((0, 0, 1, 0, 10)) + bytes(33)),   # another row
                                             (0x0F, 0x03, bytes((0, 0, 0, 0, 10)) + bytes(30))):  # wrong length
            with self.subTest(command_class=command_class, command=command, args=args[:5].hex()):
                with self.assertRaises(ValueError):
                    razer.packet(command_class, command, 0x0C, args)


class Mouse(unittest.TestCase):
    def test_a_hand_built_packet_is_never_sent(self):
        fake = FakeMouse()
        bad = bytearray(razer.mode_packet())
        bad[8] = 0x01                                       # save
        with self.assertRaises(ValueError):
            fake.mouse()._send(bytes(bad))
        self.assertEqual(fake.sent, [])

    def test_show_sends_frame_and_mode_with_a_zero_in_front(self):
        fake = FakeMouse()
        fake.mouse().show(GOLD)
        self.assertEqual(fake.sent, [b"\0" + razer.frame_packet(GOLD), b"\0" + razer.mode_packet()])
        self.assertEqual(razer.HIDIOCSFEATURE, 0xC05B4806)
        self.assertEqual(razer.HIDIOCGFEATURE, 0xC05B4807)

    def test_answers(self):
        FakeMouse([0x01, 0x02, 0x02]).mouse().show(GOLD)       # busy once: it waits and goes on
        for answer in (0x03, 0x05):
            with self.assertRaises(OSError):
                FakeMouse([answer]).mouse().show(GOLD)

    def test_finds_interface_3(self):
        with tempfile.TemporaryDirectory() as root:
            for n, interface in enumerate(("00", "01", "02", "03")):
                hid = os.path.join(root, "usb", f"1-1:1.{n}", f"0003:1532:0099.000{n}")
                write(os.path.join(hid, "uevent"), "HID_ID=0003:00001532:00000099\nHID_NAME=Razer Basilisk V3\n")
                write(os.path.join(root, "usb", f"1-1:1.{n}", "bInterfaceNumber"), interface + "\n")
                os.makedirs(os.path.join(root, "class", f"hidraw{n + 3}"))
                os.symlink(hid, os.path.join(root, "class", f"hidraw{n + 3}", "device"))
            self.assertEqual(razer.find(os.path.join(root, "class")), "/dev/hidraw6")
            os.unlink(os.path.join(root, "usb", "1-1:1.3", "bInterfaceNumber"))
            self.assertIsNone(razer.find(os.path.join(root, "class")))

    def test_no_mouse_is_an_os_error(self):
        with mock.patch.object(razer, "find", return_value=None):
            with self.assertRaises(razer.NoMouse):
                razer.Mouse()
        self.assertTrue(issubclass(razer.NoMouse, OSError))     # the service retries it


if __name__ == "__main__":
    unittest.main()

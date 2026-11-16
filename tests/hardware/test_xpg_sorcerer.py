import contextlib
import io
import os
import tempfile
import unittest

from luces.hardware import xpg_sorcerer as xpg

GOLD = (255, 137, 4)
NEVER = (0xA0, 0xA1, 0xA4, 0xA5)


class FakeKeyboard:
    """Locked, it answers each packet with a report 5; the last 0xEA of the unlock frees it. Records what it gets."""

    def __init__(self, locked=True):
        self.locked, self.sent, self.queue, self.t, self.saves = locked, [], [], 0.0, 0

    def ioctl(self, fd, request, p, *rest):
        assert request == xpg.HIDIOCSFEATURE
        p = bytes(p)
        self.sent.append(p)
        if p[1] == 0xEA:
            self.saves += 1
            if self.saves == 6 and self.sent[-2] == xpg._build(bytes.fromhex("a305014b640000ff")):
                self.locked = False
        elif self.locked:
            self.queue.append(bytes([0x05]) + bytes(63))

    def read(self, fd, n):
        if not self.queue:
            raise BlockingIOError
        return self.queue.pop(0)

    def sleep(self, s):
        self.t += s

    def clock(self):
        return self.t

    def open(self):
        with contextlib.redirect_stderr(io.StringIO()):       # the unlock says so on stderr
            return xpg.KeyboardLights("/dev/fake", ioctl=self.ioctl, read=self.read, sleep=self.sleep, clock=self.clock,
                                      open_=lambda *a: 3, close=lambda fd: None)


class Packets(unittest.TestCase):
    def test_a_canvas_frame(self):
        p0, p1 = xpg.frame(GOLD)
        self.assertEqual(len(p0), 264)
        self.assertEqual(p0[:6], bytes([0x07, 0xA3, 0x08, 0x00, 0x00, 0x00]))
        self.assertEqual(p1[:6], bytes([0x07, 0xA3, 0x08, 0x00, 0x01, 0x00]))
        self.assertEqual(p0[6:10], bytes([0x64, *GOLD]))
        self.assertEqual(p1[6:10], bytes([0x64, *GOLD]))       # cell 64 opens page 1
        self.assertEqual(p1[258:262], bytes([0x64, *GOLD]))    # cell 127, the last one
        self.assertFalse(any(p0[262:]))

    def test_a_black_cell_is_all_zeros(self):
        p0, _ = xpg.frame([(0, 0, 0), (1, 2, 3)] + [(0, 0, 0)] * 126)
        self.assertEqual(p0[6:14], bytes([0, 0, 0, 0, 0x64, 1, 2, 3]))

    def test_forbidden(self):
        for data in ([xpg.SAVE, 0], [xpg.SET_PROFILE_STATE, 0], [xpg.CHANGE_PROFILE], [xpg.SET_KEYS], [xpg.SET_MACRO],
                     [xpg.SET_INFO], [xpg.SET_EFFECT, 0, 0, 0, 100, 255, 0, 0], [xpg.SET_EFFECT, 8, 1, 0, 0],
                     [xpg.SET_EFFECT, 8, 0, 2, 0], bytes(300)):
            with self.assertRaises(xpg.Forbidden):
                xpg.packet(data)

    def test_never_these_even_inside_the_unlock(self):
        for command in NEVER:
            for unlock in (False, True):
                with self.assertRaises(xpg.Forbidden):
                    xpg.packet([command], unlock=unlock)

    def test_save_and_profile_only_with_the_exact_unlock_bytes(self):
        for hx in ("ea", "a6000000000001", "a305014b640000ff"):
            with self.assertRaises(xpg.Forbidden):
                xpg.packet(bytes.fromhex(hx))
            xpg.packet(bytes.fromhex(hx), unlock=True)
        for hx in ("ea05", "ea0001", "a6000000000005", "a300000064ff8904", "a1", "a4", "a0"):
            with self.assertRaises(xpg.Forbidden):
                xpg.packet(bytes.fromhex(hx), unlock=True)

    def test_reads_are_allowed(self):
        self.assertEqual(xpg.packet([xpg.READ_PROFILE_STATE, 0])[:3], bytes([0x07, 0xB1, 0x00]))
        self.assertEqual(xpg.packet([xpg.READ_ACTIVE_PROFILE])[:2], bytes([0x07, 0xB6]))

    def test_the_unlock(self):
        times = [ms for ms, _ in xpg.UNLOCK]
        self.assertEqual(times, sorted(times))
        self.assertEqual([hx[:2] for _, hx in xpg.UNLOCK], ["a6", "ea"] * 5 + ["a6", "a3", "ea"])
        self.assertEqual([hx for _, hx in xpg.UNLOCK][1:10:2], ["ea", "ea01", "ea02", "ea03", "ea04"])   # the 5 profiles


class KeyboardLights(unittest.TestCase):
    def setUp(self):
        xpg._unlocks.clear()

    def test_free_it_saves_nothing(self):
        fake = FakeKeyboard(locked=False)
        k = fake.open()
        self.assertFalse(k.unlocked)
        k.show(GOLD)
        self.assertTrue(all(p[1] == 0xA3 and p[2] == 8 for p in fake.sent))
        self.assertEqual(fake.sent[-2][6:10], bytes([0x64, *GOLD]))

    def test_locked_it_unlocks_once(self):
        fake = FakeKeyboard()
        k = fake.open()
        self.assertTrue(k.unlocked)
        others = [p for p in fake.sent if not (p[1] == 0xA3 and p[2] == 8)]
        self.assertEqual(others, [xpg._build(bytes.fromhex(hx)) for _, hx in xpg.UNLOCK])
        self.assertGreater(fake.t, 8.6)                  # with the timings of the vendor's software
        k.show((10, 20, 30))
        self.assertEqual(fake.saves, 6)
        self.assertFalse({p[1] for p in fake.sent} & set(NEVER))

    def test_never_two_unlocks_in_a_row(self):
        fake = FakeKeyboard()
        fake.open()
        fake.locked = True
        with self.assertRaises(xpg.Locked):
            fake.open()
        self.assertEqual(fake.saves, 6)
        fake.t += xpg.BETWEEN_UNLOCKS_S
        fake.saves = 0
        fake.open()
        self.assertEqual(fake.saves, 6)

    def test_no_more_than_48_a_day(self):
        fake = FakeKeyboard()
        xpg._unlocks.extend(-86000.0 + i * 61 for i in range(xpg.UNLOCKS_A_DAY))
        fake.t = xpg._unlocks[-1] + xpg.BETWEEN_UNLOCKS_S
        with self.assertRaisesRegex(xpg.Locked, "24 hours"):
            fake.open()
        self.assertEqual(fake.saves, 0)

    def test_it_locks_again(self):
        fake = FakeKeyboard(locked=False)
        k = fake.open()
        fake.locked = True
        with self.assertRaises(xpg.Locked):
            for _ in range(xpg.NOTICES_IN_A_ROW + 1):
                k.show((1, 2, 3))

    def test_key_reports_are_only_counted(self):
        fake = FakeKeyboard(locked=False)
        k = fake.open()
        fake.queue = [bytes([0x05, 0, 0, 0, 0, 0, 0, 0]) + bytes(range(1, 17)) + bytes(4), bytes([0x01]) + bytes(40)]
        self.assertEqual(k._notices(), 1)
        self.assertEqual(fake.queue, [])

    def test_finds_interface_2(self):
        with tempfile.TemporaryDirectory() as root:
            for n in range(3):
                hid = os.path.join(root, "usb", f"1-2:1.{n}", f"0003:125F:730E.000{n}")
                os.makedirs(hid)
                with open(os.path.join(hid, "uevent"), "w", encoding="utf-8") as f:
                    f.write("HID_ID=0003:0000125F:0000730E\n")
                with open(os.path.join(root, "usb", f"1-2:1.{n}", "bInterfaceNumber"), "w", encoding="ascii") as f:
                    f.write(f"0{n}\n")
                os.makedirs(os.path.join(root, "class", f"hidraw{n}"))
                os.symlink(hid, os.path.join(root, "class", f"hidraw{n}", "device"))
            self.assertEqual(xpg.find(os.path.join(root, "class")), "/dev/hidraw2")


if __name__ == "__main__":
    unittest.main()

import threading
import time
import unittest

from luces import emitter


class FakeDevice:
    def __init__(self, delay=0.0):
        self.colors, self.delay, self.fails, self.closed = [], delay, False, 0
        self.free = threading.Event()
        self.free.set()

    def open(self):
        if self.fails:
            raise OSError("unplugged")
        return self

    def show(self, rgb):
        self.free.wait(5)
        if self.fails:
            raise OSError("unplugged")
        if self.delay:
            time.sleep(self.delay)
        self.colors.append(rgb)

    def close(self):
        self.closed += 1


class Emitter(unittest.TestCase):
    def test_average_in_linear_light(self):
        d = FakeDevice()
        e = emitter.Emitter("gpu", d.open, interval_s=3, average=True)
        e.put((1.0, 0.0, 0.0))
        e.put((0.0, 0.0, 1.0))
        e.step(0.0)
        self.assertEqual(d.colors, [(128, 0, 128)])

    def test_without_average_the_last_one_wins(self):
        d = FakeDevice()
        e = emitter.Emitter("mouse", d.open, interval_s=0.05)
        e.put((1.0, 0.0, 0.0))
        e.put((0.0, 0.0, 1.0))
        e.step(0.0)
        self.assertEqual(d.colors, [(0, 0, 255)])

    def test_interval_only_on_change_and_refresh(self):
        d = FakeDevice()
        e = emitter.Emitter("gpu", d.open, interval_s=3, refresh_s=60, average=True)
        self.assertIsNone(e.wait(0.0))               # no color: it waits for one
        e.put((0.5, 0.5, 0.5))
        self.assertEqual(e.wait(0.0), 0.0)
        e.step(0.0)
        e.put((0.5, 0.5, 0.5))
        self.assertAlmostEqual(e.wait(1.0), 2.0)     # at most every 3 s
        e.step(3.0)
        self.assertEqual(len(d.colors), 1)           # same color: not sent
        self.assertAlmostEqual(e.wait(3.0), 3.0)     # the next decision, not before 3 s
        self.assertAlmostEqual(e.wait(6.0), 54.0)    # and with no new color, the refresh of the minute
        e.step(60.0)
        self.assertEqual(len(d.colors), 2)

    def test_reconnects(self):
        d = FakeDevice()
        e = emitter.Emitter("mouse", d.open, interval_s=0.05, retry_s=5)
        e.put((1.0, 0.0, 0.0))
        e.step(0.0)
        d.fails = True
        e.put((0.0, 1.0, 0.0))
        e.step(1.0)
        self.assertIn("unplugged", e.problem)
        self.assertEqual(d.closed, 1)
        self.assertAlmostEqual(e.wait(2.0), 4.0)
        d.fails = False
        self.assertEqual(e.wait(6.0), 0.0)
        e.step(6.0)
        self.assertEqual(d.colors, [(255, 0, 0), (0, 255, 0)])
        self.assertIsNone(e.problem)

    def test_a_refused_command_is_a_problem_not_a_crash(self):
        class Refuses(FakeDevice):
            def show(self, rgb):
                raise ValueError("not allowed")
        d = Refuses()
        e = emitter.Emitter("gpu", d.open, interval_s=3)
        e.put((1.0, 1.0, 1.0))
        e.step(0.0)
        self.assertEqual(e.problem, "gpu: not allowed")
        self.assertIsNone(e.sent)

    def test_put_never_waits_for_the_device(self):
        d = FakeDevice()
        d.free.clear()                                 # the device hangs in show
        e = emitter.Emitter("mouse", d.open, interval_s=0.0)
        e.start()
        try:
            e.put((0.1, 0.1, 0.1))
            time.sleep(0.05)
            start = time.monotonic()
            for i in range(200):
                e.put((i / 199, 0.0, 0.0))
            self.assertLess(time.monotonic() - start, 0.1)
            d.free.set()
            limit = time.monotonic() + 3
            while (not d.colors or d.colors[-1] != (255, 0, 0)) and time.monotonic() < limit:
                time.sleep(0.01)
            self.assertEqual(d.colors[-1], (255, 0, 0))
            self.assertLessEqual(len(d.colors), 3)     # not all 200: the first, maybe one in between, and the last
        finally:
            e.stop()
        self.assertEqual(d.colors[-1], (0, 0, 0))     # black on stopping


if __name__ == "__main__":
    unittest.main()

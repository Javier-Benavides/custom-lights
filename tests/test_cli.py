import contextlib
import io
import os
import time
import unittest
from unittest import mock

from luces import chip_tools, cli, desktop, paths
from luces import settings as st
from tests.helpers import PLACE, SETTINGS


class Commands(unittest.TestCase):
    def setUp(self):
        for f in os.listdir(paths.CONTROL):
            os.unlink(os.path.join(paths.CONTROL, f))
        self.notices = []
        self._notify, desktop.notify = desktop.notify, self.notices.append

    def tearDown(self):
        desktop.notify = self._notify

    def run_quietly(self, *args):
        with contextlib.redirect_stdout(io.StringIO()):
            return cli.main(list(args))

    def mode(self):
        return st.read_json(paths.control("mode.json"))

    def test_demo_goes_back_to_what_was_on(self):
        self.run_quietly("sun")
        self.assertEqual(self.run_quietly("demo", "sunset", "2", "partly"), 0)
        m = self.mode()
        self.assertEqual((m["scene"], m["back_to"], m["demo"]["weather"], m["demo"]["duration"]), ("demo", "sun", "partly", 120.0))
        self.run_quietly("demo", "storm")
        self.assertEqual(self.mode()["back_to"], "sun")

    def test_badly_written_demo(self):
        for args in (["demo"], ["demo", "hail"], ["demo", "sunset", "0"], ["demo", "sunset", "2", "hail"]):
            self.assertEqual(self.run_quietly(*args), 2)

    def test_next_after_demo_continues_from_what_was_on(self):
        self.run_quietly("sun")
        self.run_quietly("demo", "sunset")
        self.run_quietly("next")
        self.assertEqual(self.mode()["scene"], "relax")

    def test_next_goes_around(self):
        seen = []
        for _ in range(5):
            self.run_quietly("next")
            seen.append(self.mode()["scene"])
        self.assertEqual(seen, ["sun", "relax", "off", "sky", "sun"])

    def test_next_notifies_on_the_desktop(self):
        self.run_quietly("next")   # a click or the shortcut: no terminal
        self.assertEqual(self.notices, ["Sun"])

    def test_next_in_a_terminal_does_not_notify(self):
        class Terminal(io.StringIO):
            def isatty(self):
                return True

        with contextlib.redirect_stdout(Terminal()):
            cli.main(["next"])
        self.assertEqual(self.notices, [])

    def test_next_after_breathe_continues_from_what_was_on(self):
        self.run_quietly("sun")
        self.run_quietly("breathe", "5")
        self.run_quietly("next")
        self.assertEqual(self.mode()["scene"], "relax")

    def test_next_after_color_returns_to_the_cycle(self):
        self.run_quietly("color", "#FF0000")
        self.run_quietly("next")
        self.assertEqual(self.mode()["scene"], "sky")

    def test_choosing_by_hand_marks_how_long_it_lasts(self):
        before = time.time()
        self.run_quietly("relax")
        self.assertGreaterEqual(self.mode()["forced_until"], before + 2 * 3600)
        self.run_quietly("off")
        self.assertIsNone(self.mode()["forced_until"])

    def test_test_shows_the_color_as_the_service_would(self):
        r, g, b = chip_tools.test_bytes("#FF5A14", SETTINGS)
        self.assertEqual(r, 178)     # the 70 % limit
        self.assertLess(g, r / 5)    # without gamma it would be 90 of green: almost white
        self.assertLess(b, 3)

    def test_test_by_zone(self):
        asked = []
        with mock.patch.object(chip_tools, "paint_test", lambda c: asked.append(sorted(c)) or 0):
            for zone in ("case", "cooler", "all", "3"):
                self.run_quietly("test", zone, "#FF5A14")
            self.assertEqual(self.run_quietly("test", "tube", "#FF5A14"), 2)
            self.run_quietly("test-chain", "case")
        self.assertEqual(asked, [[1], [2], [1, 2], [3], [1]])

    def test_today_shows_the_stages_in_order(self):
        out = io.StringIO()
        with mock.patch.object(cli, "_place", return_value=PLACE), contextlib.redirect_stdout(out):
            self.assertEqual(cli.main(["today", "2026-11-05"]), 0)
        text = out.getvalue()
        self.assertIn("sets at", text)
        times = [line.split()[0] for line in text[text.index("Sunset"):].splitlines()[1:]]
        self.assertEqual(times, sorted(times))
        self.assertIn("gold", text)

    def test_shortcut(self):
        values = {"custom-keybindings": "@as []", "favorite-apps": "['firefox.desktop']"}
        done = []

        def gsettings(action, schema, key, value=None):
            if action == "get":
                return values[key]
            done.append((schema, key, value))
            values[key] = value
            return ""

        with contextlib.redirect_stdout(io.StringIO()):
            desktop.shortcut([], gsettings=gsettings)
            self.assertEqual(values["custom-keybindings"], str([desktop.SHORTCUT_PATH]))
            self.assertEqual(values["favorite-apps"], str(["firefox.desktop", desktop.ICON]))
            self.assertIn("<Super>F12", [d[2] for d in done])
            desktop.shortcut([], gsettings=gsettings)   # twice does not duplicate
            self.assertEqual(values["custom-keybindings"], str([desktop.SHORTCUT_PATH]))
            desktop.shortcut(["remove"], gsettings=gsettings)
        self.assertEqual(values["custom-keybindings"], "[]")
        self.assertEqual(values["favorite-apps"], str(["firefox.desktop"]))

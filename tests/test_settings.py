import os
import tempfile
import unittest

from luces import settings as st
from tests.helpers import SETTINGS


class Validation(unittest.TestCase):
    def assert_invalid(self, bad, message):
        with self.assertRaisesRegex(st.InvalidSettings, message):
            st.validate(bad)

    def test_clear_errors(self):
        self.assert_invalid({**SETTINGS, "general": {**SETTINGS["general"], "max_brightness": 500}}, "max_brightness")
        self.assert_invalid({**SETTINGS, "zones": {"case": {"header": 2, "leds": 32}, "cooler": {"header": 2, "leds": 32}}}, "same header")

    def test_a_flare_never_flashes(self):
        sun = SETTINGS["sun"]
        self.assert_invalid({**SETTINGS, "sun": {**sun, "flares": {**sun["flares"], "rise_s": 0.1}}}, "rise_s")

    def test_tongues_stay_under_the_flash_limit(self):
        self.assert_invalid({**SETTINGS, "sun": {**SETTINGS["sun"], "tongue_s": 0.2}}, "tongue_s")

    def test_unknown_zone(self):
        self.assert_invalid({**SETTINGS, "zones": {**SETTINGS["zones"], "roof": {"header": 3, "leds": 32}}}, "only accepts")

    def test_the_default_headers(self):
        self.assertEqual(SETTINGS["zones"]["case"]["header"], 1)
        self.assertEqual(SETTINGS["zones"]["cooler"]["header"], 2)

    def test_stages_must_be_sorted(self):
        sky = SETTINGS["sky"]
        self.assert_invalid({**SETTINGS, "sky": {**sky, "sunset": list(reversed(sky["sunset"]))}}, "sorted")


class Place(unittest.TestCase):
    def _load(self, text):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "place.toml")
            with open(path, "w") as f:
                f.write(text)
            return st.load_place(path)

    def test_missing_file(self):
        self.assertIsNone(st.load_place("/nonexistent/place.toml"))

    def test_valid(self):
        self.assertEqual(self._load('lat = 10.0\nlon = 20.0\nstations = ["ZZZZ"]\n')["stations"], ["ZZZZ"])

    def test_invalid(self):
        for text in ("lat = 100\nlon = 0\n", "lat = 0\nlon = 200\n", 'lat = 0\nlon = 0\nstations = ["toolong"]\n',
                     "lat = 0\nlon = 0\nbox = [1, 2, 0, 3]\n"):
            with self.assertRaises(st.InvalidSettings):
                self._load(text)

    def test_the_example_is_valid(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.assertIsNotNone(st.load_place(os.path.join(root, "system", "place.example.toml")))

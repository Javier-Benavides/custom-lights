import os
import struct
import unittest
import zlib

from luces import paths, settings
from luces.data import fetch, metar, png, satellite, solar_indices, update
from luces.data.fetch import InvalidData
from tests.helpers import epoch

NOW = epoch(2026, 11, 5, 14, 20, 0)
ADJUST = {"contrast": 14, "margin_k": 8}
SOLAR_TEXT = """#                Last 30 Days Daily Solar Data
#  Date     10.7cm Number  Hemis. Regions Field  Flux   C  M  X  S  1  2  3
#---------------------------------------------------------------------------
2026 11 03  100   41      180      0    -999      *   1  0  0  1  0  0  0
2026 11 04  111   64      240      1    -999      *   3  0  0  4  0  0  0
"""


def make_png(pixels, width, filter_type=0):
    def chunk(kind, body):
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body))

    raw, previous = bytearray(), bytes(width * 4)
    for y in range(len(pixels) // width):
        row = bytes(v for p in pixels[y * width:(y + 1) * width] for v in p)
        raw.append(filter_type)
        for i, value in enumerate(row):
            a = row[i - 4] if i >= 4 else 0
            b = previous[i]
            c = previous[i - 4] if i >= 4 else 0
            p = a + b - c
            prediction = {0: 0, 1: a, 2: b, 3: (a + b) // 2, 4: min((a, b, c), key=lambda v: (abs(p - v), (a, b, c).index(v)))}[filter_type]
            raw.append((value - prediction) & 255)
        previous = row
    header = struct.pack(">IIBBBBB", width, len(pixels) // width, 8, 6, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(bytes(raw))) + chunk(b"IEND", b"")


class SolarIndices(unittest.TestCase):
    def test_last_row(self):
        d = solar_indices.parse(SOLAR_TEXT, 1000.0)
        self.assertEqual((d["date"], d["flux"], d["sunspots"], d["area"], d["c"]), ("2026-11-04", 111, 64, 240, 3))

    def test_skips_rows_without_flux(self):
        d = solar_indices.parse(SOLAR_TEXT + "2026 11 05 -999  -999 -999 -999 -999 * -1 -1 -1 0 0 0 0\n", 1000.0)
        self.assertEqual(d["date"], "2026-11-04")

    def test_changed_format(self):
        with self.assertRaises(InvalidData):
            solar_indices.parse("<html>error</html>", 1000.0)


class Png(unittest.TestCase):
    def test_every_filter(self):
        pixels = [(x * 13 % 256, x * 7 % 256, x * 3 % 256, 255) for x in range(36)]
        for filter_type in range(5):
            self.assertEqual(png.read_png(make_png(pixels, 6, filter_type)), pixels)

    def test_a_strange_file_does_not_break_it(self):
        for bad in (b"<xml>error</xml>", make_png([(1, 2, 3, 255)] * 4, 2)[:40]):
            with self.assertRaises(InvalidData):
                png.read_png(bad)


class CloudFraction(unittest.TestCase):
    def test_clean_ground_has_no_clouds(self):
        self.assertEqual(satellite.cloud_fraction([(80 + i % 5,) * 3 + (255,) for i in range(100)], 20, ADJUST), 0.0)

    def test_thin_clouds_are_counted_against_the_ground(self):
        self.assertAlmostEqual(satellite.cloud_fraction([(80, 80, 80, 255)] * 70 + [(100, 100, 100, 255)] * 30, 20, ADJUST), 0.3)

    def test_full_cover_is_seen_against_the_air(self):
        self.assertEqual(satellite.cloud_fraction([(150, 150, 150, 255)] * 100, 20, ADJUST), 1.0)

    def test_the_very_cold_comes_in_color_and_is_cloud(self):
        self.assertAlmostEqual(satellite.cloud_fraction([(80, 80, 80, 255)] * 75 + [(0, 200, 255, 255)] * 25, 20, ADJUST), 0.25)

    def test_image_not_published_yet(self):
        self.assertIsNone(satellite.cloud_fraction([(0, 0, 0, 0)] * 100, 20, ADJUST))


class Update(unittest.TestCase):
    def setUp(self):
        for folder in (paths.CONTROL, paths.DATA):
            for f in os.listdir(folder):
                os.unlink(os.path.join(folder, f))

    def _place(self, extra=""):
        with open(paths.control("place.toml"), "w") as f:
            f.write(f'lat = 10.0\nlon = 20.0\nstations = ["ZZZZ"]\n{extra}')

    def _with_satellite(self, fetch_image):
        self._place("box = [9.5, 19.5, 10.5, 20.5]\n")
        report = "ZZZZ 051400Z 00000KT CAVOK 20/10 Q1014"
        return update.update(NOW, fetch=lambda url: report if "metar" in url else SOLAR_TEXT, fetch_image=fetch_image)

    def test_the_satellite_sees_what_cavok_does_not_report(self):
        asked = []
        image = make_png([(80, 80, 80, 255)] * 60 + [(110, 110, 110, 255)] * 40, 10)
        self.assertEqual(self._with_satellite(lambda url: asked.append(url) or image), 0)
        w = settings.read_json(paths.data("weather.json"))
        self.assertEqual(w["airport_coverage"], 0.0)
        self.assertEqual(w["coverage"], 0.4)
        self.assertIn("BBOX=9.5,19.5,10.5,20.5", asked[0])
        self.assertLess(NOW - w["satellite_time"], 3600)

    def test_an_unpublished_image_tries_an_earlier_one(self):
        empty, full = make_png([(0, 0, 0, 0)] * 100, 10), make_png([(80, 80, 80, 255)] * 100, 10)
        answers = [empty, empty, full]
        self.assertEqual(self._with_satellite(lambda url: answers.pop(0)), 0)
        self.assertEqual(answers, [])
        self.assertEqual(settings.read_json(paths.data("weather.json"))["satellite_coverage"], 0.0)

    def test_without_satellite_the_airport_stays(self):
        def fail(url):
            raise InvalidData("no network")

        self.assertEqual(self._with_satellite(fail), 0)
        w = settings.read_json(paths.data("weather.json"))
        self.assertEqual(w["coverage"], 0.0)
        self.assertNotIn("satellite_coverage", w)

    def test_a_failure_does_not_erase_what_was_there(self):
        settings.write_json(paths.data("weather.json"), {"time": 1, "coverage": 0.5})
        settings.write_json(paths.data("solar.json"), {"fetched": 0})
        self._place()

        def fail(url):
            raise InvalidData("no network")

        self.assertEqual(update.update(200000.0, fetch=fail), 2)
        self.assertEqual(settings.read_json(paths.data("weather.json"))["coverage"], 0.5)

    def test_the_sun_is_fetched_once_a_day(self):
        asked = []
        settings.write_json(paths.data("solar.json"), {"fetched": 1000.0})
        update.update(1000.0 + 3600, fetch=lambda url: asked.append(url) or SOLAR_TEXT)
        self.assertEqual(asked, [])
        update.update(1000.0 + 21 * 3600, fetch=lambda url: asked.append(url) or SOLAR_TEXT)
        self.assertEqual(asked, [solar_indices.URL])


class Fetch(unittest.TestCase):
    def test_every_url_is_https(self):
        for url in (metar.URL, solar_indices.URL, satellite.URL):
            self.assertTrue(url.startswith("https://"))

    def test_the_user_agent_says_nothing_personal(self):
        self.assertRegex(fetch.USER_AGENT, r"^luces/[0-9.]+$")

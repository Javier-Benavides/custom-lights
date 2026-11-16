import unittest

from luces.data import metar
from luces.data.fetch import InvalidData
from tests.helpers import epoch

NOW = epoch(2026, 11, 5, 14, 20, 0)


class Metar(unittest.TestCase):
    def test_clear(self):
        d = metar.parse("METAR ZZZZ 051400Z VRB03KT CAVOK 20/11 Q1014 NOSIG=", NOW)
        self.assertEqual((d["coverage"], d["kind"]), (0.0, None))
        self.assertEqual(d["time"], epoch(2026, 11, 5, 14, 0, 0))

    def test_takes_the_most_covered_layer(self):
        self.assertEqual(metar.parse("ZZZZ 051400Z 18008KT 9999 FEW020 SCT040 BKN100 15/08 Q1020", NOW)["coverage"], 0.75)

    def test_keeps_the_height_of_the_layer_that_leads(self):
        d = metar.parse("ZZZZ 051400Z 18008KT 9999 FEW020 BKN100 15/08 Q1020", NOW)
        self.assertAlmostEqual(d["cloud_height_km"], 3.05, places=2)
        self.assertIsNone(metar.parse("ZZZZ 051400Z 18008KT CAVOK 15/08 Q1020", NOW)["cloud_height_km"])

    def test_observed_rain(self):
        d = metar.parse("ZZZZ 051400Z 18008KT 5000 -RA BKN015 OVC030 12/10 Q1012", NOW)
        self.assertEqual((d["coverage"], d["kind"]), (1.0, "rain"))

    def test_the_forecast_does_not_count(self):
        d = metar.parse("ZZZZ 051400Z 18008KT 9999 FEW040 15/08 Q1020 TEMPO 3000 RA BKN010", NOW)
        self.assertEqual((d["coverage"], d["kind"]), (0.2, None))

    def test_nearby_and_recent_weather_do_not_count(self):
        self.assertIsNone(metar.parse("ZZZZ 051400Z 18008KT 9999 VCSH SCT040 15/08 Q1020 RERA", NOW)["kind"])

    def test_cloud_with_a_type(self):
        self.assertEqual(metar.parse("ZZZZ 051400Z 18008KT 9999 SCT030CB OVC080 15/08 Q1020", NOW)["coverage"], 1.0)

    def test_a_storm_wins(self):
        self.assertEqual(metar.parse("ZZZZ 051400Z 18008KT 3000 TSRA BR OVC020 15/08 Q1010", NOW)["kind"], "storm")

    def test_month_change(self):
        d = metar.parse("ZZZZ 312350Z 00000KT CAVOK 15/08 Q1020", epoch(2026, 11, 1, 0, 5, 0))
        self.assertEqual(d["time"], epoch(2026, 10, 31, 23, 50, 0))

    def test_prefers_the_first_station_if_fresh(self):
        text = "METAR AAAA 051400Z 00000KT 9999 OVC020 20/10 Q1015\nMETAR BBBB 051400Z 00000KT CAVOK 20/10 Q1015"
        d = metar.parse(text, NOW, ["AAAA", "BBBB"])
        self.assertEqual((d["station"], d["coverage"]), ("AAAA", 1.0))

    def test_if_the_first_is_asleep_it_uses_the_backup(self):
        text = "METAR AAAA 042300Z 00000KT 9999 OVC020 20/10 Q1015\nMETAR BBBB 051400Z 00000KT CAVOK 20/10 Q1015"
        d = metar.parse(text, NOW, ["AAAA", "BBBB"])
        self.assertEqual((d["station"], d["coverage"]), ("BBBB", 0.0))

    def test_a_broken_line_does_not_drop_the_others(self):
        self.assertEqual(metar.parse("garbage\nMETAR BBBB 051400Z 00000KT CAVOK 20/10 Q1015", NOW, ["AAAA", "BBBB"])["station"], "BBBB")

    def test_invalid(self):
        for text in ("", "hello", "ZZZZ 051400Z 18008KT 15/08 Q1020"):
            with self.assertRaises(InvalidData):
                metar.parse(text, NOW)

    def test_high_clouds_weigh_less(self):
        self.assertAlmostEqual(metar.parse("ZZZZ 051400Z 25005KT 9999 BKN170 23/11 Q1014", NOW)["coverage"], 0.45)
        self.assertEqual(metar.parse("ZZZZ 051400Z 25005KT 9999 BKN030 23/11 Q1014", NOW)["coverage"], 0.75)

    def test_temperature_below_zero(self):
        self.assertEqual(metar.parse("ZZZZ 051400Z 00000KT CAVOK M03/M05 Q1014", NOW)["temperature"], -3)

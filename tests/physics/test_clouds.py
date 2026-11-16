import unittest

from luces.physics import clouds

THIN = 0.65
COLORS = clouds.CloudColors((1, 1, 1), (1, 0.8, 0.3), (1, 0.66, 0.53), (1, 0.5, 0.5), (0.78, 0.77, 1))


def overhead(t, coverage):
    return clouds.cloud_overhead(t, coverage)


class Coverage(unittest.TestCase):
    def test_clouds_cover_what_the_data_says(self):
        for coverage in (0.2, 0.5, 0.8):
            covered = [overhead(1.79e9 + s * 2.0, coverage) for s in range(43200)]
            with_cloud = sum(1 for n in covered if n >= THIN / 2) / len(covered)
            self.assertAlmostEqual(with_cloud, coverage, delta=0.03)
            self.assertGreater(max(covered), 0.9)
            self.assertLess(min(covered), 0.1)

    def _stretches(self, coverage):
        """How long each stretch with a cloud and each gap of sky lasts, in six hours."""
        stretches, current, length = {True: [], False: []}, None, 0
        for s in range(21600):
            cloud = overhead(1.79e9 + s, coverage) >= THIN / 2
            if cloud == current:
                length += 1
            else:
                if current is not None:
                    stretches[current].append(length)
                current, length = cloud, 1
        return stretches

    def test_the_sky_shows_often_between_clouds(self):
        s = self._stretches(0.7)
        self.assertGreater(len(s[False]) / 6, 30)                 # over 30 gaps an hour
        self.assertGreater(sum(s[True]), 2 * sum(s[False]))       # but cloud dominates
        self.assertLess(sorted(s[True])[len(s[True]) // 2], 60)   # usually under a minute without seeing the sky
        self.assertLess(max(s[True]), 600)
        self.assertGreater(max(s[False]) - min(s[False]), 20)     # small gaps and big ones

    def test_a_cloud_has_no_fixed_color(self):
        for coverage in (0.7, 1.0):
            inside = [n for n in (overhead(1.79e9 + s, coverage) for s in range(3600)) if n >= THIN]
            self.assertGreater(max(inside) - min(inside), 0.25)

    def test_no_clouds_means_none_and_overcast_never_opens(self):
        self.assertEqual({overhead(s * 7.0, 0.0) for s in range(500)}, {0.0})
        self.assertGreaterEqual(min(overhead(s * 7.0, 1.0) for s in range(500)), THIN)


class EarthShadow(unittest.TestCase):
    def test_a_higher_cloud_stays_lit_for_longer(self):
        self.assertAlmostEqual(clouds.earth_shadow_depth(6.0), 2.99, places=2)
        self.assertLess(clouds.earth_shadow_depth(3.0), clouds.earth_shadow_depth(6.0))
        self.assertEqual(clouds.sun_seen_by_cloud(-1.0, 6.0), -1.0)
        self.assertGreater(clouds.sun_seen_by_cloud(-1.0, 9.0), -1.0)

    def test_a_cloud_in_shadow_is_gray(self):
        self.assertEqual(clouds.cloud_color(-3, COLORS), COLORS.gray)
        self.assertEqual(clouds.cloud_color(-2, COLORS), COLORS.afterglow)
        self.assertEqual(clouds.cloud_color(12, COLORS), COLORS.white)

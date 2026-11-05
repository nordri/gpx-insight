"""Deterministic checks of the GPX metrics contract."""
import unittest
from datetime import datetime, timedelta, timezone
from analytics.metrics import compute_basic_metrics, haversine


T0 = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)


def point(east_m=0, ele=100, seconds=0):
    # Use haversine itself only for coordinate placement; test expected geometry
    # with independent simple assertions on classified proportions.
    return {"lat": 0.0, "lon": east_m / 111195.0, "ele": ele,
            "time": T0 + timedelta(seconds=seconds)}


class MetricsTests(unittest.TestCase):
    def test_haversine_known_equatorial_degree(self):
        self.assertAlmostEqual(haversine(0, 0, 0, 1), 111194.93, delta=1)

    def test_flat_route_time_and_speed(self):
        result = compute_basic_metrics([point(0, 100, 0), point(1000, 100, 600)])
        self.assertAlmostEqual(result["distance_km"], 1.0, delta=0.01)
        self.assertEqual(result["elevation_gain_m"], 0)
        self.assertEqual(result["elevation_loss_m"], 0)
        self.assertEqual(result["total_time"], "0:10:00")
        self.assertAlmostEqual(result["avg_speed_total"], 6.0, delta=0.1)
        self.assertAlmostEqual(result["flat_ratio_pct"], 100.0, delta=0.1)

    def test_ascent_descent_and_extremes(self):
        result = compute_basic_metrics([
            point(0, 100, 0), point(100, 110, 100),
            point(200, 90, 200), point(300, 100, 300),
        ])
        self.assertEqual(result["elevation_gain_m"], 20)
        self.assertEqual(result["elevation_loss_m"], 20)
        self.assertEqual(result["elevation_max_m"], 110)
        self.assertEqual(result["elevation_min_m"], 90)
        self.assertAlmostEqual(result["uphill_ratio_pct"], 66.7, delta=0.2)
        self.assertAlmostEqual(result["downhill_ratio_pct"], 33.3, delta=0.2)

    def test_all_route_distance_is_classified(self):
        # A trailing 5m segment must not disappear from slope accounting.
        result = compute_basic_metrics([point(0, 100, 0), point(100, 100, 100),
                                        point(105, 100, 105)])
        classified = (result["uphill_ratio_pct"] + result["downhill_ratio_pct"]
                      + result["flat_ratio_pct"])
        self.assertAlmostEqual(classified, 100.0, delta=0.2)

    def test_empty_input_has_clear_error(self):
        with self.assertRaises(ValueError):
            compute_basic_metrics([])


if __name__ == "__main__":
    unittest.main()

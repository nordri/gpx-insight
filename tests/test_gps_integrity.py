"""Regression contracts for route geometry and time consistency."""
import unittest
from datetime import datetime, timedelta, timezone

from analytics.metrics import compute_basic_metrics

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


def point(meters, seconds):
    return {"lat": 0.0, "lon": meters / 111195.0, "ele": 100.0,
            "time": T0 + timedelta(seconds=seconds)}


class GPSIntegrity(unittest.TestCase):
    def test_out_and_back_gps_spike_does_not_inflate_distance(self):
        # True movement: 0 -> 100 -> 200 m. One impossible GPS outlier
        # between the two valid fixes jumps 10 km away and back in 2 s.
        points = [point(0, 0), point(100, 100),
                  point(10100, 101), point(200, 102), point(300, 202)]
        result = compute_basic_metrics(points)
        self.assertAlmostEqual(result["distance_total_m"], 300, delta=2)
        self.assertAlmostEqual(result["distance_km"], 0.3, delta=0.05)
        self.assertAlmostEqual(
            result["uphill_ratio_pct"] + result["downhill_ratio_pct"]
            + result["flat_ratio_pct"], 100, delta=0.2)

    def test_non_monotonic_timestamps_are_not_trusted(self):
        result = compute_basic_metrics([
            point(0, 0), point(100, 100), point(200, 50)])
        self.assertFalse(result["has_timestamps"])
        self.assertIsNone(result["total_time"])


if __name__ == "__main__":
    unittest.main()

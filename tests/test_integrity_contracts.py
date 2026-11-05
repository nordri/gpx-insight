"""Additional contracts for GPS integrity; expected to expose current defects."""
import unittest
from datetime import datetime, timedelta, timezone
from analytics.metrics import compute_basic_metrics

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)

def point(m, seconds, ele=100):
    return {"lat": 0.0, "lon": m / 111195.0, "ele": ele,
            "time": None if seconds is None else T0 + timedelta(seconds=seconds)}

class IntegrityContracts(unittest.TestCase):
    def test_missing_time_does_not_produce_speed(self):
        result = compute_basic_metrics([point(0, None), point(100, None)])
        self.assertFalse(result['has_timestamps'])
        self.assertIsNone(result['total_time'])
        self.assertIsNone(result['avg_speed_total'])
        self.assertIsNone(result['avg_speed_moving'])
        self.assertIsNone(result['max_speed'])

    def test_out_of_order_time_does_not_produce_speed(self):
        result = compute_basic_metrics([point(0, 0), point(100, 10), point(200, 5)])
        self.assertFalse(result['has_timestamps'])
        self.assertIsNone(result['avg_speed_total'])
        self.assertIsNone(result['avg_speed_moving'])

    def test_valid_slow_out_and_back_is_not_discarded(self):
        result = compute_basic_metrics([point(0, 0), point(100, 100),
                                        point(0, 200), point(100, 300)])
        self.assertAlmostEqual(result['distance_total_m'], 300, delta=2)
        self.assertEqual(result['point_count'], 4)

if __name__ == '__main__':
    unittest.main()

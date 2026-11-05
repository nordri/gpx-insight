"""Regression candidates for metrics not yet certified."""
import unittest
from datetime import datetime, timedelta, timezone
from analytics.metrics import compute_basic_metrics

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)

def p(m, ele=100, seconds=0, timed=True):
    return {'lat': 0., 'lon': m / 111195., 'ele': ele,
            'time': T0 + timedelta(seconds=seconds) if timed else None}

class EdgeCases(unittest.TestCase):
    def test_stationary_pause(self):
        r = compute_basic_metrics([p(0,seconds=0),p(100,seconds=100),p(100,seconds=700),p(200,seconds=800)])
        self.assertEqual(r['stopped_time'], '0:10:00')
        self.assertEqual(r['moving_time'], '0:03:20')

    def test_missing_timestamps_are_not_reported_as_zero_duration(self):
        r = compute_basic_metrics([p(0,timed=False),p(100,timed=False)])
        self.assertFalse(r['has_timestamps'])
        # A zero duration is not a measured duration; currently output uses '0:00:00'.
        self.assertNotEqual(r['total_time'], '0:00:00')

    def test_gps_spike_does_not_define_maximum_speed(self):
        r = compute_basic_metrics([p(0,seconds=0),p(100,seconds=100),p(1100,seconds=101),p(1200,seconds=201)])
        self.assertLess(r['max_speed'], 100)

    def test_noise_does_not_create_illusory_ascent(self):
        pts = [p(i*10,100+(1 if i%2 else 0),i*10) for i in range(101)]
        r = compute_basic_metrics(pts)
        self.assertLess(r['elevation_gain_m'], 10)

if __name__ == '__main__':
    unittest.main()

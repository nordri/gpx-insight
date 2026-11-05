import unittest
from datetime import datetime, timedelta, timezone
from analytics.metrics import compute_basic_metrics

class ElevationRegression(unittest.TestCase):
    def test_gradual_real_climb_is_preserved(self):
        t = datetime(2026, 1, 1, tzinfo=timezone.utc)
        pts = [dict(lat=0., lon=i*10/111195., ele=100+i, time=t+timedelta(seconds=i*10)) for i in range(101)]
        r = compute_basic_metrics(pts)
        self.assertEqual(r['elevation_gain_m'], 100)
        self.assertEqual(r['elevation_loss_m'], 0)

    def test_gentle_reversal_is_not_lost(self):
        t = datetime(2026, 1, 1, tzinfo=timezone.utc)
        elevations = [100,101,102,103,104,105,104,103,102,101,100]
        pts = [dict(lat=0., lon=i*10/111195., ele=ele, time=t+timedelta(seconds=i*10)) for i,ele in enumerate(elevations)]
        r = compute_basic_metrics(pts)
        self.assertEqual(r['elevation_gain_m'], 5)
        self.assertEqual(r['elevation_loss_m'], 5)

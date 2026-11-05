"""End-to-end fixture contract: parser -> metrics, no renderer."""
from pathlib import Path
import unittest

try:
    from parser.gpx_loader import load_gpx
except ModuleNotFoundError as exc:
    if exc.name != 'gpxpy':
        raise
    load_gpx = None
from analytics.metrics import compute_basic_metrics


@unittest.skipIf(load_gpx is None, 'gpxpy dependency is not installed')
class GPXIntegration(unittest.TestCase):
    def test_fixture_through_real_parser_and_engine(self):
        path = Path(__file__).resolve().parents[1] / 'test.gpx'
        metadata, points = load_gpx(str(path))
        self.assertEqual(len(points), 41)
        result = compute_basic_metrics(points)
        self.assertAlmostEqual(result['distance_total_m'], 1000, delta=2)
        self.assertEqual(result['elevation_gain_m'], 100)
        self.assertEqual(result['elevation_loss_m'], 100)
        self.assertEqual(result['total_time'], '1:00:00')
        self.assertAlmostEqual(result['uphill_ratio_pct'] +
                               result['downhill_ratio_pct'] +
                               result['flat_ratio_pct'], 100, delta=0.2)


if __name__ == '__main__':
    unittest.main()

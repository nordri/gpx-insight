"""Independent checks for the deterministic GPX fixture (stdlib only)."""
import math
import unittest
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

FIXTURE = Path(__file__).resolve().parents[1] / 'test.gpx'
NS = {'g': 'http://www.topografix.com/GPX/1/1'}


def great_circle_m(a, b):
    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)
    h = math.sin((lat2-lat1)/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2
    return 2 * 6371000 * math.asin(min(1, math.sqrt(h)))


class FixtureContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = ET.parse(FIXTURE).getroot()
        cls.points = root.findall('.//g:trkpt', NS)
        cls.elevations = [float(p.find('g:ele', NS).text) for p in cls.points]
        cls.times = [datetime.fromisoformat(p.find('g:time', NS).text.replace('Z', '+00:00')) for p in cls.points]

    def test_point_count(self):
        self.assertEqual(len(self.points), 41)

    def test_distance(self):
        coords = [(float(p.get('lat')), float(p.get('lon'))) for p in self.points]
        distance = sum(great_circle_m(a, b) for a, b in zip(coords, coords[1:]))
        self.assertAlmostEqual(distance, 1000, delta=0.2)

    def test_elevation_gain_loss(self):
        deltas = [b-a for a, b in zip(self.elevations, self.elevations[1:])]
        self.assertAlmostEqual(sum(max(d, 0) for d in deltas), 100, places=3)
        self.assertAlmostEqual(sum(max(-d, 0) for d in deltas), 100, places=3)
        self.assertEqual((self.elevations[0], self.elevations[-1]), (1000, 1000))

    def test_duration(self):
        self.assertEqual((self.times[-1]-self.times[0]).total_seconds(), 3600)
        self.assertTrue(all(b > a for a, b in zip(self.times, self.times[1:])))

    def test_pause_is_slow_movement_not_stationary(self):
        gaps = [(b-a).total_seconds() for a, b in zip(self.times, self.times[1:])]
        self.assertEqual(max(gaps), 600)
        self.assertEqual(gaps.count(600), 1)
        i = gaps.index(600)
        a, b = self.points[i:i+2]
        self.assertGreater(great_circle_m((float(a.get('lat')), float(a.get('lon'))), (float(b.get('lat')), float(b.get('lon')))), 20)


if __name__ == '__main__':
    unittest.main()

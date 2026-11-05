import unittest
from rendering.canvas import _fmt_speed, _fmt_time


class RenderContract(unittest.TestCase):
    def test_missing_speed_is_not_zero(self):
        self.assertEqual(_fmt_speed(None), 'N/D')

    def test_actual_zero_speed_remains_zero(self):
        self.assertEqual(_fmt_speed(0), '0.0 km/h')

    def test_missing_time_is_not_zero(self):
        self.assertEqual(_fmt_time(None), 'N/D')

    def test_valid_time_remains_unchanged(self):
        self.assertEqual(_fmt_time('01:00:00'), '01:00:00')

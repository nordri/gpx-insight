"""Regression: the extreme-grades footer must be in the exported story."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from rendering import outdoor


class ExtremeGradesIntegrationTests(unittest.TestCase):
    def test_render_story_calls_extreme_card_and_preserves_canvas_height(self):
        metrics = {
            'distance_km': 10.78, 'elevation_gain_m': 801, 'elevation_loss_m': 806,
            'total_time': 9900, 'moving_time': 9800, 'stopped_time': 100,
            'avg_speed_total': 3.9, 'max_speed': 8.0,
            'start_time': 0, 'end_time': 9900,
            'max_up_grade_pct': 45.0, 'max_down_grade_pct': -34.8,
            'avg_up_grade_pct': 16.6, 'avg_down_grade_pct': -15.3,
            'elevation_start_m': 900, 'elevation_end_m': 905, 'point_count': 100,
        }
        with tempfile.TemporaryDirectory() as directory:
            chart = Path(directory) / 'chart.png'
            output = Path(directory) / 'story.png'
            Image.new('RGBA', (600, 200), '#14251B').save(chart)
            original = outdoor.draw_extreme_grades_card
            seen = []
            def track(*args, **kwargs):
                seen.append((args[1], args[2], args[3], args[4]))
                return original(*args, **kwargs)
            with patch.object(outdoor, 'scenic_header'), \
                 patch.object(outdoor, 'footer_landscape'), \
                 patch.object(outdoor, 'draw_extreme_grades_card', side_effect=track), \
                 patch.object(outdoor, 'draw_slope_distribution_card'), \
                 patch.object(outdoor, 'draw_grade_analysis_card'), \
                 patch.object(outdoor, 'draw_flat_sections_card'):
                outdoor.render_outdoor_story({'name': 'Ruta de prueba'}, metrics, chart, output)
            self.assertEqual(len(seen), 1)
            x, y, w, h = seen[0]
            self.assertEqual((x, y, h), (0, 0, 240))  # Painter uses a local off-screen layer
            self.assertGreaterEqual(w, 450)
            with Image.open(output) as img:
                self.assertEqual(img.size, (outdoor.W, outdoor.H))
                self.assertEqual(img.height, 1920)

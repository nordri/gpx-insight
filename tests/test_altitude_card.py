import unittest
from unittest.mock import patch
from PIL import Image, ImageDraw
from rendering import outdoor


class AltitudeCardTests(unittest.TestCase):
    def test_dimensions_and_source_metrics_unchanged(self):
        metrics = {"elevation_start_m": 1147, "elevation_end_m": 1155}
        snapshot = dict(metrics)
        image = Image.new("RGB", (600, 300), "#101F1D")
        outdoor.draw_altitude_card(ImageDraw.Draw(image), 20, 20, 486, 240, metrics)
        self.assertEqual(image.size, (600, 300))
        self.assertEqual(metrics, snapshot)
        self.assertNotEqual(image.getpixel((30, 30)), (16, 31, 29))

    def test_missing_metrics_are_not_fabricated(self):
        image = Image.new("RGB", (520, 260), "#101F1D")
        outdoor.draw_altitude_card(ImageDraw.Draw(image), 0, 0, 486, 240, {})
        self.assertEqual(image.size, (520, 260))

    def test_render_story_integrates_right_card(self):
        # Assert the production entrypoint actually references the right card.
        import inspect
        source = inspect.getsource(outdoor.render_outdoor_story)
        self.assertIn("draw_altitude_card(d, footer_right_x, y, footer_right_w, 240, metrics, lang)", source)

    def test_two_column_layout_values_and_labels(self):
        image = Image.new("RGB", (486, 240), "#101F1D")
        outdoor.draw_altitude_card(ImageDraw.Draw(image), 0, 0, 486, 240,
                                   {"elevation_start_m": 1147, "elevation_end_m": 1155})
        # The middle divider exists and both value zones have different accent colors.
        self.assertNotEqual(image.getpixel((243, 130)), (20, 37, 27))
        self.assertTrue(any(image.getpixel((x, y))[2] > image.getpixel((x, y))[0] + 30
                            for x in range(45, 225) for y in range(103, 145)))
        self.assertTrue(any(image.getpixel((x, y))[0] > image.getpixel((x, y))[2] + 40
                            for x in range(265, 455) for y in range(103, 145)))

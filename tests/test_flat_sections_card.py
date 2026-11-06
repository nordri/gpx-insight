import unittest
from PIL import Image, ImageDraw
from rendering.outdoor import draw_flat_sections_card

class FlatSectionsCardTests(unittest.TestCase):
    def test_card_renders_and_does_not_mutate_metrics(self):
        metrics = {"flat_distance_km": 1.23, "flat_ratio_pct": 11.4}
        image = Image.new("RGB", (988, 51), "white")
        draw_flat_sections_card(ImageDraw.Draw(image), 0, 0, 988, 51, metrics)
        self.assertEqual(image.size, (988, 51))
        self.assertEqual(metrics, {"flat_distance_km": 1.23, "flat_ratio_pct": 11.4})
        self.assertNotEqual(image.getpixel((10, 10)), (255, 255, 255))

    def test_center_card_triptych_dimensions(self):
        image = Image.new("RGB", (988, 258), "white")
        draw_flat_sections_card(ImageDraw.Draw(image), 374, 0, 240, 258, {"flat_distance_km": 7.13, "flat_ratio_pct": 59.1})
        self.assertEqual(image.size, (988, 258))
        self.assertNotEqual(image.getpixel((400, 20)), (255, 255, 255))

    def test_missing_metrics_do_not_raise(self):
        image = Image.new("RGB", (988, 51), "white")
        draw_flat_sections_card(ImageDraw.Draw(image), 0, 0, 988, 51, {})

import unittest
from PIL import Image
from rendering.outdoor import W, H, footer_landscape

class FooterLandscapeTests(unittest.TestCase):
    def test_footer_preserves_canvas_and_draws_scene(self):
        image = Image.new('RGB', (W, H), '#14251B')
        footer_landscape(image, 1234)
        self.assertEqual(image.size, (W, H))
        self.assertNotEqual(image.getpixel((W // 2, H - 80)), (20, 37, 27))

    def test_landscape_is_deterministic(self):
        first = Image.new('RGB', (W, H), '#14251B')
        second = Image.new('RGB', (W, H), '#14251B')
        footer_landscape(first, 1234)
        footer_landscape(second, 1234)
        self.assertEqual(first.tobytes(), second.tobytes())

    def test_text_region_and_forest_have_distinct_content(self):
        image = Image.new('RGB', (W, H), '#14251B')
        footer_landscape(image, 2145)
        # Landscape has variation across the full height, not a dead bottom band.
        bottom = [image.getpixel((x, H - 3)) for x in range(0, W, 11)]
        self.assertGreater(len(set(bottom)), 1)
        top = [image.getpixel((x, H - 90)) for x in range(0, W, 11)]
        self.assertGreater(len(set(top)), 1)

    def test_zero_points_is_not_missing(self):
        image = Image.new('RGB', (W, H), '#14251B')
        footer_landscape(image, 0)
        self.assertEqual(image.size, (W, H))

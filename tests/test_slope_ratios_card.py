import unittest
from PIL import Image, ImageDraw
from rendering.outdoor import draw_slope_ratios_card, _slope_ring


class SlopeRatiosCardTests(unittest.TestCase):
    def test_card_renders_without_changing_metrics(self):
        image = Image.new('RGB', (540, 340), '#101F1D')
        metrics = {'uphill_ratio_pct': 45.5, 'downhill_ratio_pct': 48.8,
                   'ascent_per_km': 74.7, 'descent_per_km': 74.0}
        original = dict(metrics)
        labels = {'slope_ratios': 'Ratios de pendiente',
                  'uphill_ratio': 'Ratio subida', 'downhill_ratio': 'Ratio bajada'}
        draw_slope_ratios_card(ImageDraw.Draw(image), 20, 20, 500, 278, metrics, labels)
        self.assertEqual(metrics, original)
        self.assertNotEqual(image.getpixel((145, 110)), image.getpixel((20, 20)))

    def test_ring_edge_cases(self):
        for value in (None, 0, 45.5, 100, -2, 110):
            with self.subTest(value=value):
                image = Image.new('RGB', (120, 120), '#182A1F')
                _slope_ring(ImageDraw.Draw(image), 60, 60, value, '#A3E635')
                self.assertEqual(image.size, (120, 120))


if __name__ == '__main__':
    unittest.main()

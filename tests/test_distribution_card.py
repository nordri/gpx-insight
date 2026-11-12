import unittest
from PIL import Image, ImageDraw
from rendering.outdoor import _distribution_bins, draw_slope_distribution_card

class DistributionCardTests(unittest.TestCase):
    def setUp(self):
        self.metrics = {
            'uphill_table': [{'route_pct': p, 'label': l} for p,l in zip((5,8,10,17),('> 15%','10–15%','5–10%','1–5%'))],
            'flat_ratio_pct': 12,
            'downhill_table': [{'route_pct': p, 'label': l} for p,l in zip((18,14,10,6),('1–5%','5–10%','10–15%','> 15%'))],
        }
    def test_bins_are_normalized_and_ordered(self):
        bins = _distribution_bins(self.metrics)
        self.assertEqual(len(bins), 9)
        self.assertAlmostEqual(sum(row[0] for row in bins), 1)
        self.assertEqual(bins[0][1], '> 15%')
        self.assertEqual(bins[-1][1], '> 15%')
    def test_missing_distribution_renders_without_fabricated_values(self):
        img = Image.new('RGB', (1080, 1920), 'white')
        draw_slope_distribution_card(ImageDraw.Draw(img), 46, 1325, 988, 150, {})
        self.assertEqual(img.size, (1080, 1920))
        self.assertEqual(img.getpixel((51, 1400)), (17, 34, 23))

    def test_card_renders_without_changing_dimensions(self):
        img = Image.new('RGB',(1080,1920),'white')
        draw_slope_distribution_card(ImageDraw.Draw(img),46,1325,988,150,self.metrics)
        self.assertEqual(img.size,(1080,1920))
        self.assertEqual(img.getpixel((46+5,1325+75)),(17,34,23))

if __name__ == '__main__': unittest.main()

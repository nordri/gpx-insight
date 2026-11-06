import unittest
from PIL import Image, ImageDraw
from rendering.outdoor import draw_extreme_grades_card

class ExtremeGradesCardTests(unittest.TestCase):
    def test_card_dimensions_and_empty_metrics(self):
        img = Image.new('RGB', (560, 280), '#101F1D')
        draw_extreme_grades_card(ImageDraw.Draw(img), 20, 20, 520, 240, {})
        self.assertEqual(img.size, (560, 280))
        self.assertNotEqual(img.getpixel((40, 40)), (16, 31, 29))

    def test_negative_descent_is_displayable(self):
        img = Image.new('RGB', (560, 280), '#101F1D')
        draw_extreme_grades_card(ImageDraw.Draw(img), 20, 20, 520, 240,
                                 {'max_down_grade_pct': -34.8, 'avg_down_grade_pct': -15.3})
        self.assertEqual(img.size, (560, 280))

import unittest
from PIL import Image, ImageDraw
from rendering.outdoor import draw_grade_analysis_card

class GradeAnalysisCardTests(unittest.TestCase):
    def test_both_cards_render_without_mutating_metrics(self):
        rows = [{'label': label, 'distance_km': 1.2, 'route_pct': 11.1} for label in ('> 15%', '10–15%', '5–10%', '1–5%')]
        original = [dict(row) for row in rows]
        image = Image.new('RGB', (1080, 350), '#FFFFFF')
        for direction, x in [('up', 46), ('down', 550)]:
            draw_grade_analysis_card(ImageDraw.Draw(image), x, 30, 480, 260, rows, 4.88, direction)
        self.assertEqual(image.size, (1080, 350))
        self.assertEqual(rows, original)
        self.assertNotEqual(image.getpixel((80, 65)), (255,255,255))

    def test_missing_data_is_not_presented_as_zero(self):
        image = Image.new('RGB', (500, 280), '#FFFFFF')
        draw_grade_analysis_card(ImageDraw.Draw(image), 0, 0, 480, 260, [], None)
        self.assertEqual(image.size, (500, 280))

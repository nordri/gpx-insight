import unittest
from PIL import Image, ImageDraw
from rendering.outdoor import draw_times_card, TIME_ICON_COLOR, TIME_CARD_ICONS


class TimesCardTests(unittest.TestCase):
    def test_icon_palette_and_solid_runner(self):
        self.assertEqual(TIME_ICON_COLOR, '#E6EBD9')
        self.assertIn('fill="currentColor"', TIME_CARD_ICONS['runner'])

    def test_four_cells_and_dividers_are_visible(self):
        image = Image.new('RGB', (520, 320), '#1c3024')
        draw = ImageDraw.Draw(image)
        data = [('En movimiento', '2:40:34', 'es'),
                ('Parado', '0:02:01', 'es'),
                ('Vel. media total', '4.0 km/h', 'es'),
                ('Vel. máxima', '8.9 km/h', 'es')]
        draw_times_card(draw, 15, 15, 490, 285, data)
        self.assertNotEqual(image.getpixel((260, 140)), (28, 48, 36))
        self.assertTrue(any(image.getpixel((xx, 145)) != (28, 48, 36) for xx in range(35, 120)))


if __name__ == '__main__':
    unittest.main()

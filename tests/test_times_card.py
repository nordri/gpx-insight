import unittest
from PIL import Image, ImageDraw
from rendering.outdoor import draw_times_card, TIME_ICON_COLOR, TIME_CARD_ICONS


class TimesCardTests(unittest.TestCase):
    def test_icon_palette_and_solid_runner(self):
        self.assertEqual(TIME_ICON_COLOR, '#E6EBD9')
        self.assertIn('fill="currentColor"', TIME_CARD_ICONS['runner'])

    def test_four_cells_and_dividers_are_visible(self):
        # Test the card at its actual 230 px layout height, without rescaling.
        image = Image.new('RGB', (520, 260), '#1c3024')
        draw = ImageDraw.Draw(image)
        data = [('En movimiento', '2:40:34', 'es'),
                ('Parado', '0:02:01', 'es'),
                ('Vel. media total', '4.0 km/h', 'es'),
                ('Vel. máxima', '8.9 km/h', 'es')]
        draw_times_card(draw, 15, 15, 490, 230, data)

        background = (28, 48, 36)
        # Each cell must contain visible content; avoid relying on a single
        # pixel position inherited from the old 285 px layout.
        quadrants = [(25, 76, 259, 157), (261, 76, 504, 157),
                     (25, 159, 259, 244), (261, 159, 504, 244)]
        for x1, y1, x2, y2 in quadrants:
            with self.subTest(region=(x1, y1, x2, y2)):
                self.assertTrue(any(
                    image.getpixel((xx, yy)) != background
                    for yy in range(y1, y2)
                    for xx in range(x1, x2)
                ))

        # Dividers are defined by the geometry, not the old cell positions.
        self.assertNotEqual(image.getpixel((260, 110)), background)
        self.assertNotEqual(image.getpixel((100, 154)), background)


if __name__ == '__main__':
    unittest.main()

import unittest
from unittest.mock import ANY, patch

from PIL import Image, ImageDraw
from i18n import TRANSLATIONS
from rendering.outdoor import draw_times_card, TIME_ICON_COLOR, TIME_CARD_ICONS


class TimesCardTests(unittest.TestCase):
    def test_icon_palette_and_solid_runner(self):
        self.assertEqual(TIME_ICON_COLOR, '#E6EBD9')
        self.assertIn('fill="currentColor"', TIME_CARD_ICONS['runner'])

    def test_four_cells_and_dividers_are_visible(self):
        # Test the card at its actual 230 px layout height, without rescaling.
        image = Image.new('RGB', (520, 260), '#1c3024')
        draw = ImageDraw.Draw(image)
        data = [('En movimiento', '2:40:34'),
                ('Parado', '0:02:01'),
                ('Vel. media total', '4.0 km/h'),
                ('Vel. máxima', '8.9 km/h')]
        draw_times_card(draw, 15, 15, 490, 230, data, lang="es")

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

    def test_heading_uses_requested_language(self):
        image = Image.new("RGB", (520, 260), "#1c3024")
        with patch("rendering.outdoor._time_text") as draw_text:
            draw_times_card(
                ImageDraw.Draw(image),
                15,
                15,
                490,
                230,
                [("MOVING", "1:00"), ("STOPPED", "0:00"), ("AVG", "4.0"), ("MAX", "8.0")],
                lang="en",
            )

        draw_text.assert_any_call(
            ANY,
            ANY,
            TRANSLATIONS["en"]["times_speeds"],
            20,
            "#FFFFFF",
            "bold",
        )


if __name__ == '__main__':
    unittest.main()

import unittest
from PIL import Image, ImageDraw
from rendering.canvas import _fit_title_lines, _route_date_label
from datetime import datetime


class VisualLayoutTests(unittest.TestCase):
    def setUp(self):
        self.draw = ImageDraw.Draw(Image.new("RGB", (1080, 200)))

    def test_long_title_fits_two_lines(self):
        text = "Wikiloc - Pico Perdiguera, Pico de la Pala y Peña La Carcamala desde Miraflores de la Sierra"
        lines, font = _fit_title_lines(self.draw, text, max_width=1000)
        self.assertLessEqual(len(lines), 2)
        for line in lines:
            self.assertLessEqual(self.draw.textlength(line, font=font), 1000)

    def test_short_title_is_not_truncated(self):
        lines, _ = _fit_title_lines(self.draw, "Ruta circular", max_width=1000)
        self.assertEqual(lines, ["Ruta circular"])

    def test_spanish_date(self):
        label = _route_date_label({"time": datetime(2025, 5, 29)}, "es")
        self.assertIn("mayo", label)
        self.assertIn("2025", label)


if __name__ == "__main__":
    unittest.main()

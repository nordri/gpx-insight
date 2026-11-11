import unittest
from PIL import Image, ImageDraw
from rendering.outdoor import _header_title_lines, scenic_header, ROW_HEIGHTS, W, H, INNER, font


class HeaderStoryTests(unittest.TestCase):
    def setUp(self):
        self.draw = ImageDraw.Draw(Image.new('RGB', (W, H)))

    def test_wikiloc_prefix_removed(self):
        self.assertEqual(_header_title_lines(self.draw, 'Wikiloc - Ruta circular'), ['Ruta circular'])

    def test_long_title_is_two_lines_with_three_dots(self):
        lines = _header_title_lines(self.draw, 'Wikiloc - ' + 'Ruta de montaña ' * 30)
        self.assertEqual(len(lines), 2)
        self.assertTrue(lines[-1].endswith('...'))
        for line in lines:
            self.assertLessEqual(self.draw.textlength(line, font=font(38, True)), INNER)

    def test_header_does_not_change_canvas(self):
        image = Image.new('RGB', (W, H), 'white')
        scenic_header(image, ROW_HEIGHTS[0])
        self.assertEqual(image.size, (1080, 1920))
        self.assertEqual(image.getpixel((0, ROW_HEIGHTS[0] + 1)), (255, 255, 255))


if __name__ == '__main__':
    unittest.main()

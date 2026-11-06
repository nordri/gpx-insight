import unittest
from unittest.mock import patch
from rendering.canvas import render_story
from rendering.outdoor import _f, _grade


class OutdoorRenderTests(unittest.TestCase):
    def test_missing_metric_is_not_rendered_as_zero(self):
        self.assertEqual(_f(None), 'N/D')
        self.assertEqual(_grade(None), 'N/D')

    def test_forest_theme_uses_outdoor_renderer(self):
        with patch('rendering.outdoor.render_outdoor_story') as renderer:
            render_story({}, {}, 'chart.png', 'output.png', theme='forest', lang='es')
            renderer.assert_called_once_with({}, {}, 'chart.png', 'output.png', lang='es')


if __name__ == '__main__':
    unittest.main()

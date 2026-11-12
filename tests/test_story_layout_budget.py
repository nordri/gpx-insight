"""Regression guard for the 9:16 outdoor layout budget."""
import unittest
from rendering import outdoor


class StoryLayoutBudgetTests(unittest.TestCase):
    def test_fixed_story_dimensions(self):
        self.assertEqual((outdoor.W, outdoor.H), (1080, 1920))
        self.assertEqual(outdoor.M, 40)
        self.assertEqual(outdoor.INNER, 1000)

    def test_vertical_budget(self):
        self.assertEqual(outdoor.GAP, 16)
        self.assertEqual(outdoor.ROW_HEIGHTS,
                         (220, 100, 35, 462, 230, 150, 260, 200, 135))
        self.assertEqual(outdoor.TOP_MARGIN + outdoor.BOTTOM_MARGIN +
                         sum(outdoor.ROW_HEIGHTS) +
                         outdoor.GAP * (len(outdoor.ROW_HEIGHTS) - 1), 1920)

    def test_summary_follows_header_without_dead_space(self):
        header_end = outdoor.TOP_MARGIN + outdoor.ROW_HEIGHTS[0]
        summary_top = header_end + outdoor.GAP
        self.assertEqual(summary_top - header_end, 16)
        self.assertEqual(summary_top, 236)

    def test_footer_is_anchored_to_bottom(self):
        footer_top = (outdoor.TOP_MARGIN + sum(outdoor.ROW_HEIGHTS[:-1])
                      + outdoor.GAP * (len(outdoor.ROW_HEIGHTS) - 1))
        self.assertEqual(footer_top, outdoor.H - outdoor.ROW_HEIGHTS[-1])
        self.assertEqual(footer_top + outdoor.ROW_HEIGHTS[-1], 1920)

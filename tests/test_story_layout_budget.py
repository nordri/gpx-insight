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
                         (320, 100, 35, 340, 220, 130, 260, 190, 100))
        self.assertEqual(outdoor.TOP_MARGIN + outdoor.BOTTOM_MARGIN +
                         sum(outdoor.ROW_HEIGHTS) +
                         outdoor.GAP * (len(outdoor.ROW_HEIGHTS) - 1), 1920)

import os
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from gpxpy.gpx import GPXXMLSyntaxException
from PIL import Image

from service import generate_story


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "test.gpx"


class StoryServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gpx_content = FIXTURE.read_bytes()

    def _temporary_service_directories(self):
        return set(Path(tempfile.gettempdir()).glob("gpx-insight-*"))

    def test_generate_story_from_bytes_returns_1080x1920_png_outside_repo_cwd(self):
        original_cwd = Path.cwd()
        before = self._temporary_service_directories()
        with tempfile.TemporaryDirectory() as working_directory:
            try:
                os.chdir(working_directory)
                story = generate_story(self.gpx_content)
                self.assertEqual(list(Path(working_directory).iterdir()), [])
            finally:
                os.chdir(original_cwd)

        self.assertTrue(story.startswith(b"\x89PNG\r\n\x1a\n"))
        with Image.open(BytesIO(story)) as image:
            self.assertEqual(image.format, "PNG")
            self.assertEqual(image.size, (1080, 1920))
            image.verify()
        self.assertEqual(self._temporary_service_directories(), before)

    def test_explicit_english_generates_a_1080x1920_png(self):
        story = generate_story(self.gpx_content, lang="en")

        self.assertTrue(story.startswith(b"\x89PNG\r\n\x1a\n"))
        with Image.open(BytesIO(story)) as image:
            self.assertEqual(image.size, (1080, 1920))
            image.verify()

    def test_english_alternative_theme_generates_a_png(self):
        story = generate_story(self.gpx_content, theme="alpine", lang="en")

        self.assertTrue(story.startswith(b"\x89PNG\r\n\x1a\n"))
        with Image.open(BytesIO(story)) as image:
            self.assertEqual(image.size, (1080, 1920))
            image.verify()

    def test_empty_corrupt_and_pointless_gpx_are_rejected_and_cleaned(self):
        cases = (
            (b"", ValueError),
            (b"<gpx", GPXXMLSyntaxException),
            (b'<gpx xmlns="http://www.topografix.com/GPX/1/1"></gpx>', ValueError),
        )
        for content, error in cases:
            with self.subTest(content=content[:12]):
                before = self._temporary_service_directories()
                with self.assertRaises(error):
                    generate_story(content)
                self.assertEqual(self._temporary_service_directories(), before)

    def test_unsupported_theme_and_language_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unsupported theme"):
            generate_story(self.gpx_content, theme="unknown")
        with self.assertRaisesRegex(ValueError, "Unsupported language"):
            generate_story(self.gpx_content, lang="fr")

    def test_non_bytes_gpx_content_is_rejected(self):
        with self.assertRaisesRegex(TypeError, "gpx_content must be bytes"):
            generate_story("not bytes")

    def test_default_language_is_passed_to_chart_and_renderer(self):
        with (
            patch("service.load_gpx", return_value=({}, [])),
            patch("service.compute_basic_metrics", return_value={}),
            patch("service.generate_elevation_chart", return_value="chart.png") as chart,
            patch(
                "service.render_story",
                side_effect=lambda **kwargs: Path(kwargs["output_path"]).write_bytes(b"png"),
            ) as renderer,
        ):
            self.assertEqual(generate_story(b"<gpx/>"), b"png")

        self.assertEqual(chart.call_args.kwargs["lang"], "es")
        self.assertEqual(renderer.call_args.kwargs["lang"], "es")


if __name__ == "__main__":
    unittest.main()

"""End-to-end smoke tests: real GPX -> CLI -> PNG. Requires project dependencies."""
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'test.gpx'


class CLIEndToEnd(unittest.TestCase):
    def _run_cli(self, source: Path, output: Path):
        return subprocess.run(
            [sys.executable, str(ROOT / 'cli.py'), '--input', str(source),
             '--output', str(output), '--lang', 'es'],
            cwd=ROOT, text=True, capture_output=True, timeout=90,
        )

    def _assert_png(self, output: Path):
        self.assertTrue(output.is_file(), 'CLI did not produce PNG')
        with Image.open(output) as img:
            self.assertEqual(img.format, 'PNG')
            self.assertEqual(img.size, (1080, 2140))
            img.verify()

    def test_fixture_generates_valid_story(self):
        self.assertTrue(FIXTURE.exists(), 'test.gpx is required')
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'story.png'
            result = self._run_cli(FIXTURE, output)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self._assert_png(output)

    def test_missing_timestamps_generates_valid_story(self):
        self.assertTrue(FIXTURE.exists(), 'test.gpx is required')
        original = FIXTURE.read_text(encoding='utf-8')
        # Remove timestamps from track points only; metadata timestamp is unrelated.
        altered, count = re.subn(
            r'(<trkpt\b[^>]*>.*?)<time>[^<]*</time>', r'\1', original,
            flags=re.DOTALL,
        )
        self.assertGreater(count, 0, 'Fixture has no track point timestamps')
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'no-times.gpx'
            output = Path(tmp) / 'no-times.png'
            source.write_text(altered, encoding='utf-8')
            result = self._run_cli(source, output)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self._assert_png(output)


if __name__ == '__main__':
    unittest.main()

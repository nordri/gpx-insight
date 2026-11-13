from pathlib import Path
from tempfile import TemporaryDirectory

from analytics.metrics import compute_basic_metrics
from parser.gpx_loader import load_gpx
from rendering.canvas import FALLBACK_I18N, THEMES, render_story
from rendering.charts import THEME_COLORS, generate_elevation_chart


SUPPORTED_THEMES = frozenset(THEMES).intersection(THEME_COLORS)
SUPPORTED_LANGUAGES = frozenset(FALLBACK_I18N)


def generate_story(
    gpx_content: bytes,
    theme: str = "forest",
    lang: str = "en",
) -> bytes:
    if not isinstance(gpx_content, bytes):
        raise TypeError("gpx_content must be bytes")
    if not gpx_content.strip():
        raise ValueError("GPX content must not be empty")
    if not isinstance(theme, str):
        raise TypeError("theme must be a string")
    if theme not in SUPPORTED_THEMES:
        raise ValueError(f"Unsupported theme: {theme}")
    if not isinstance(lang, str):
        raise TypeError("lang must be a string")
    if lang not in SUPPORTED_LANGUAGES:
        raise ValueError(f"Unsupported language: {lang}")

    with TemporaryDirectory(prefix="gpx-insight-") as directory:
        temp_dir = Path(directory)
        gpx_path = temp_dir / "input.gpx"
        chart_output_path = temp_dir / "elevation_profile.png"
        story_path = temp_dir / "story.png"

        gpx_path.write_bytes(gpx_content)
        metadata, points = load_gpx(str(gpx_path))
        metrics = compute_basic_metrics(points)
        chart_path = generate_elevation_chart(
            metrics,
            theme=theme,
            lang=lang,
            output_path=str(chart_output_path),
        )
        render_story(
            metadata=metadata,
            metrics=metrics,
            chart_path=chart_path,
            output_path=story_path,
            theme=theme,
            lang=lang,
        )
        return story_path.read_bytes()

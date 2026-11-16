import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import ANY, patch

from matplotlib.axes import Axes

from i18n import DEFAULT_LANG, TRANSLATIONS
from rendering.canvas import _fmt_speed, _route_date_label
from rendering.charts import generate_elevation_chart


class InternationalizationTests(unittest.TestCase):
    def test_translation_keys_are_complete_and_default_to_spanish(self):
        self.assertEqual(DEFAULT_LANG, "es")
        self.assertEqual(set(TRANSLATIONS["es"]), set(TRANSLATIONS["en"]))
        self.assertEqual(TRANSLATIONS["es"]["flat_subtitle"], "Pendiente < 1 %")
        self.assertEqual(TRANSLATIONS["en"]["flat_subtitle"], "Grade < 1%")

    def test_date_and_missing_value_follow_the_selected_language(self):
        metadata = {"time": datetime(2024, 5, 4)}

        self.assertEqual(
            _route_date_label(metadata, "es"),
            "Sábado, 4 de mayo de 2024",
        )
        self.assertEqual(
            _route_date_label(metadata, "en"),
            "Saturday, 04 May 2024",
        )
        self.assertEqual(_fmt_speed(None, TRANSLATIONS["en"]), "N/A")

    def test_chart_axes_use_translations_and_extra_y_axis_padding(self):
        points = {
            "distance_series_km": [0.0, 1.0, 2.0],
            "elevation_series_m": [100.0, 120.0, 110.0],
        }

        with tempfile.TemporaryDirectory() as directory:
            for language, options in (("es", {}), ("en", {"lang": "en"})):
                with (
                    patch.object(Axes, "set_xlabel", autospec=True) as set_xlabel,
                    patch.object(Axes, "set_ylabel", autospec=True) as set_ylabel,
                ):
                    generate_elevation_chart(
                        points,
                        **options,
                        output_path=str(Path(directory) / f"{language}.png"),
                    )

                set_xlabel.assert_called_once_with(
                    ANY,
                    TRANSLATIONS[language]["distance_axis"],
                    color=ANY,
                    fontsize=11,
                    labelpad=10,
                )
                set_ylabel.assert_called_once_with(
                    ANY,
                    TRANSLATIONS[language]["elevation_axis"],
                    color=ANY,
                    fontsize=11,
                    labelpad=14,
                )


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

from typing import Any

import gpxpy


def load_gpx(path: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
	with open(path, "r", encoding="utf-8") as f:
		gpx = gpxpy.parse(f)

	gpx_metadata = getattr(gpx, "metadata", None)
	route_name = (
		getattr(gpx_metadata, "name", None)
		or getattr(gpx, "name", None)
		or "Unnamed Route"
	)
	route_time = (
		getattr(gpx_metadata, "time", None)
		or getattr(gpx, "time", None)
	)

	metadata = {
		"name": route_name,
		"time": route_time,
	}

	points: list[dict[str, Any]] = []

	for track in gpx.tracks:
		for segment in track.segments:
			for point in segment.points:
				points.append(
					{
						"lat": point.latitude,
						"lon": point.longitude,
						"ele": point.elevation or 0.0,
						"time": point.time,
					}
				)

	if not points:
		raise ValueError("No track points found in GPX file")

	return metadata, points

# GPX Hiking Story Generator

Instagram-ready hiking analytics generator from Wikiloc GPX tracks.

---

# Project Goals

* Input: GPX file from Wikiloc
* Output: PNG 1080x1920 optimized for Instagram stories
* Activity: Hiking only (v1)
* Style: Clean / premium / data-focused
* Themes: Supported via configuration
* Language: Multi-language ready

---

# Planned Stack

```txt
Python 3.12+

gpxpy
numpy
pandas
matplotlib
Pillow
scipy
```

---

# Project Structure

```txt
gpx-insight/
├── cli.py
├── requirements.txt
├── assets/
│   ├── fonts/
│   ├── icons/
│   └── themes/
├── parser/
│   └── gpx_loader.py
├── analytics/
│   ├── metrics.py
│   ├── slopes.py
│   ├── elevation.py
│   ├── difficulty.py
│   └── movement.py
├── rendering/
│   ├── canvas.py
│   ├── cards.py
│   ├── charts.py
│   ├── hero.py
│   └── themes.py
├── i18n/
│   ├── en.json
│   └── es.json
└── output/
```

---

# requirements.txt

```txt
gpxpy
numpy
pandas
matplotlib
Pillow
scipy
```

---

# CLI Design

```bash
python cli.py \
  --input route.gpx \
  --output route.png \
  --theme forest \
  --lang en
```

---

# Example Theme Definitions

```python
THEMES = {
    "forest": {
        "background": "#101512",
        "primary": "#88c57f",
        "secondary": "#4f6f52",
        "accent": "#d6f5c3",
        "text": "#f5f5f5"
    },
    "volcanic": {
        "background": "#140d0d",
        "primary": "#d14d3f",
        "secondary": "#7f1d1d",
        "accent": "#ffb4a2",
        "text": "#ffffff"
    },
    "alpine": {
        "background": "#0f1720",
        "primary": "#7dd3fc",
        "secondary": "#155e75",
        "accent": "#e0f2fe",
        "text": "#ffffff"
    }
}
```

---

# Difficulty System

## Formula

```python
score = (
    distance_km * 1.0 +
    elevation_gain_m * 0.015 +
    steep_ratio * 20
)
```

Where:

* distance_km = total route distance
* elevation_gain_m = total ascent
* steep_ratio = percentage of route over 15% grade

---

# Difficulty Levels

| Score | Label     | Theme Bias |
| ----- | --------- | ---------- |
| 0-20  | EASY      | Green      |
| 20-40 | MODERATE  | Lime       |
| 40-60 | HARD      | Orange     |
| 60-80 | VERY HARD | Red        |
| 80+   | BRUTAL    | Deep Red   |

---

# GPX Parsing Strategy

## Metadata

Extract:

* Route name
* Route date
* Author (optional)

## Trackpoints

Extract:

* Latitude
* Longitude
* Elevation
* Timestamp

---

# Example GPX Loader

```python
import gpxpy
from datetime import datetime


def load_gpx(path: str):
    with open(path, "r", encoding="utf-8") as f:
        gpx = gpxpy.parse(f)

    metadata = {
        "name": gpx.metadata.name if gpx.metadata else "Unnamed Route",
        "time": gpx.metadata.time if gpx.metadata else None
    }

    points = []

    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                points.append({
                    "lat": point.latitude,
                    "lon": point.longitude,
                    "ele": point.elevation,
                    "time": point.time
                })

    return metadata, points
```

---

# Elevation Smoothing

Noise reduction is critical.

Planned approach:

```python
from scipy.signal import savgol_filter

smoothed = savgol_filter(elevations, 21, 3)
```

Benefits:

* Removes GPS spikes
* Produces cleaner elevation profile
* More realistic grade calculations

---

# Distance Calculation

Using haversine approximation.

```python
from math import radians, sin, cos, sqrt, atan2


def haversine(lat1, lon1, lat2, lon2):
    R = 6371000

    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)

    a = (
        sin(dlat / 2) ** 2 +
        cos(radians(lat1)) *
        cos(radians(lat2)) *
        sin(dlon / 2) ** 2
    )

    return 2 * R * atan2(sqrt(a), sqrt(1 - a))
```

---

# Movement Detection

Trackpoints with:

* speed < 0.7 km/h
* for at least 90 seconds

will be considered stopped time.

---

# Highest Point Detection

Simplified v1:

```python
highest_point = max(points, key=lambda p: p["ele"])
```

---

# Elevation Profile

Central visual element.

Features:

* Smooth curve
* Gradient fill
* Highest point marker
* Distance labels
* Theme-aware colors

---

# Layout Draft

```txt
┌─────────────────────────────┐
│ HEADER                      │
│ Route name                  │
│ Date                         │
│ Hero mountain profile       │
├─────────────────────────────┤
│ MAIN METRICS                │
│ Distance / Elevation        │
│ Time / Speed                │
├─────────────────────────────┤
│ ELEVATION PROFILE           │
├─────────────────────────────┤
│ DIFFICULTY + SLOPES         │
├─────────────────────────────┤
│ TECHNICAL DETAILS           │
└─────────────────────────────┘
```

---

# Planned Visual Features

## Dynamic Theme Selection

Theme automatically adapts according to difficulty:

* EASY → greens
* HARD → orange
* BRUTAL → red/dark

---

# Text Handling

Long route names:

* Maximum 2 lines
* Font auto-scaling
* Graceful truncation

---

# Multi-language Design

## Example EN

```json
{
  "distance": "Distance",
  "elevation": "Elevation",
  "moving_time": "Moving Time"
}
```

## Example ES

```json
{
  "distance": "Distancia",
  "elevation": "Desnivel",
  "moving_time": "Tiempo en movimiento"
}
```

---

# Future Ideas (v2)

* Multi-activity support
* Topographic maps
* GPX comparison mode
* Historical stats
* Weather integration
* Strava export
* Batch generation
* Animated reels

---

# Immediate Next Step

Implement:

1. GPX parser
2. Distance/elevation calculations
3. Elevation smoothing
4. Basic matplotlib profile
5. Pillow canvas composition
6. Final PNG export

---

# First Working Implementation (MVP)

## cli.py

```python
import argparse
from parser.gpx_loader import load_gpx
from analytics.metrics import compute_basic_metrics
from rendering.charts import generate_elevation_chart
from rendering.canvas import render_story


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--input", required=True)
    parser.add_argument("--output", default="output/story.png")
    parser.add_argument("--theme", default="forest")
    parser.add_argument("--lang", default="en")

    args = parser.parse_args()

    metadata, points = load_gpx(args.input)

    metrics = compute_basic_metrics(points)

    chart_path = generate_elevation_chart(
        points,
        theme=args.theme
    )

    render_story(
        metadata=metadata,
        metrics=metrics,
        chart_path=chart_path,
        output_path=args.output,
        theme=args.theme,
        lang=args.lang
    )

    print(f"Story generated: {args.output}")


if __name__ == "__main__":
    main()
```

---

# analytics/metrics.py

```python
from math import radians, sin, cos, sqrt, atan2
from datetime import timedelta


EARTH_RADIUS = 6371000


DIFFICULTY_LEVELS = [
    (20, "EASY"),
    (40, "MODERATE"),
    (60, "HARD"),
    (80, "VERY HARD"),
    (999, "BRUTAL")
]


# Haversine distance in meters

def haversine(lat1, lon1, lat2, lon2):
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)

    a = (
        sin(dlat / 2) ** 2 +
        cos(radians(lat1)) *
        cos(radians(lat2)) *
        sin(dlon / 2) ** 2
    )

    return 2 * EARTH_RADIUS * atan2(sqrt(a), sqrt(1 - a))


# Compute route metrics

def compute_basic_metrics(points):
    total_distance = 0
    elevation_gain = 0
    elevation_loss = 0

    speeds = []
    stopped_seconds = 0

    highest_point = max(points, key=lambda p: p["ele"])

    for i in range(1, len(points)):
        prev = points[i - 1]
        curr = points[i]

        distance = haversine(
            prev["lat"],
            prev["lon"],
            curr["lat"],
            curr["lon"]
        )

        total_distance += distance

        delta_ele = curr["ele"] - prev["ele"]

        if delta_ele > 0:
            elevation_gain += delta_ele
        else:
            elevation_loss += abs(delta_ele)

        if prev["time"] and curr["time"]:
            delta_time = (
                curr["time"] - prev["time"]
            ).total_seconds()

            if delta_time > 0:
                speed_kmh = (distance / delta_time) * 3.6
                speeds.append(speed_kmh)

                if speed_kmh < 0.7:
                    stopped_seconds += delta_time

    start_time = points[0]["time"]
    end_time = points[-1]["time"]

    total_time = end_time - start_time
    moving_time = total_time - timedelta(seconds=stopped_seconds)

    avg_speed = (
        (total_distance / 1000) /
        (moving_time.total_seconds() / 3600)
    ) if moving_time.total_seconds() > 0 else 0

    max_speed = max(speeds) if speeds else 0

    steep_ratio = min(elevation_gain / max(total_distance, 1), 1)

    difficulty_score = (
        (total_distance / 1000) * 1.0 +
        elevation_gain * 0.015 +
        steep_ratio * 20
    )

    difficulty_label = next(
        label for threshold, label in DIFFICULTY_LEVELS
        if difficulty_score <= threshold
    )

    return {
        "distance_km": round(total_distance / 1000, 1),
        "elevation_gain_m": int(elevation_gain),
        "elevation_loss_m": int(elevation_loss),
        "total_time": str(total_time).split(".")[0],
        "moving_time": str(moving_time).split(".")[0],
        "avg_speed": round(avg_speed, 1),
        "max_speed": round(max_speed, 1),
        "highest_point": int(highest_point["ele"]),
        "difficulty_score": int(difficulty_score),
        "difficulty_label": difficulty_label
    }
```

---

# rendering/charts.py

```python
import matplotlib.pyplot as plt
from scipy.signal import savgol_filter


THEME_COLORS = {
    "forest": "#88c57f",
    "volcanic": "#d14d3f",
    "alpine": "#7dd3fc"
}


# Generate elevation profile image

def generate_elevation_chart(points, theme="forest"):
    elevations = [p["ele"] for p in points]

    if len(elevations) > 21:
        elevations = savgol_filter(elevations, 21, 3)

    color = THEME_COLORS.get(theme, "#88c57f")

    fig, ax = plt.subplots(figsize=(10, 3))

    ax.plot(elevations, linewidth=3, color=color)
    ax.fill_between(range(len(elevations)), elevations, alpha=0.25)

    ax.set_xticks([])
    ax.set_yticks([])

    for spine in ax.spines.values():
        spine.set_visible(False)

    plt.tight_layout()

    output_path = "output/elevation_profile.png"

    plt.savefig(
        output_path,
        transparent=True,
        dpi=200
    )

    plt.close()

    return output_path
```

---

# rendering/canvas.py

```python
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont


WIDTH = 1080
HEIGHT = 1920


THEMES = {
    "forest": {
        "background": "#101512",
        "text": "#ffffff",
        "accent": "#88c57f"
    },
    "volcanic": {
        "background": "#140d0d",
        "text": "#ffffff",
        "accent": "#d14d3f"
    },
    "alpine": {
        "background": "#0f1720",
        "text": "#ffffff",
        "accent": "#7dd3fc"
    }
}


# Render final story image

def render_story(
    metadata,
    metrics,
    chart_path,
    output_path,
    theme="forest",
    lang="en"
):
    colors = THEMES[theme]

    img = Image.new(
        "RGB",
        (WIDTH, HEIGHT),
        colors["background"]
    )

    draw = ImageDraw.Draw(img)

    title_font = ImageFont.load_default()
    body_font = ImageFont.load_default()

    route_name = metadata["name"][:60]

    draw.text(
        (80, 80),
        route_name,
        fill=colors["text"],
        font=title_font
    )

    draw.text(
        (80, 140),
        f'Distance: {metrics["distance_km"]} km',
        fill=colors["text"],
        font=body_font
    )

    draw.text(
        (80, 190),
        f'Elevation: +{metrics["elevation_gain_m"]} m',
        fill=colors["text"],
        font=body_font
    )

    draw.text(
        (80, 240),
        f'Difficulty: {metrics["difficulty_label"]}',
        fill=colors["accent"],
        font=body_font
    )

    chart = Image.open(chart_path)

    chart = chart.resize((920, 300))

    img.paste(chart, (80, 420), chart)

    img.save(output_path)
```

---

# Example Execution

```bash
python cli.py \
  --input route.gpx \
  --output output/story.png \
  --theme forest \
  --lang en
```

---

# MVP Goal

Generate a complete first PNG containing:

* Route name
* Distance
* Elevation gain
* Difficulty label
* Elevation profile
* Theme-aware colors

Once the pipeline works end-to-end, we iterate visually.

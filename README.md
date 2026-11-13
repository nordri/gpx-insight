# GPX Insight

GPX Insight is a Python tool that analyzes GPX files from outdoor activities and generates visual reports containing detailed route metrics.

## Purpose

The goal of GPX Insight is to transform raw GPX data into a clear, visually appealing, and easy-to-share report.

Using recorded GPS points, the tool calculates metrics such as:

- Total distance.
- Cumulative elevation gain and loss.
- Maximum and minimum elevation.
- Elevation profile.
- Total, moving, and stopped time.
- Speed and pace.
- Gradient distribution.
- Uphill, downhill, and flat section analysis.
- Maximum and minimum gradients.

The output is a **1080 × 1920 pixel (9:16) PNG image**, optimized for Instagram Stories, Reels, and other mobile formats.

GPX Insight aims to provide accurate, reproducible results calculated directly from GPX data, without relying on external platforms or services.

## Usage

### Requirements

- Python 3.
- A valid GPX file containing route points.

### Installation and setup

Clone the repository and navigate to the project directory.

Use the project `Makefile` to set up the environment and install dependencies:

```bash
make setup
```

This creates the virtual environment and installs the required Python packages.

### Generate a report

The preferred way to run the analysis is through the project target that wraps the CLI:

```bash
make analyze GPX=route.gpx
```

By default, the generated report is saved to:

```text
output/story.png
```

To specify a custom output path and options, use:

```bash
make analyze GPX=route.gpx OUTPUT=output/my-route.png THEME=forest LANG=es
```

### Makefile targets

| Target | Description | Example |
|---|---|---|
| `make setup` | Creates the virtual environment and installs dependencies. | `make setup` |
| `make check` | Verifies runtime dependencies. | `make check` |
| `make analyze` | Generates the report from a GPX file. | `make analyze GPX=route.gpx` |
| `make test` | Runs the unit and integration test suite. | `make test` |
| `make docker-build` | Builds the AWS Lambda Python 3.12 base image. | `make docker-build DOCKER_IMAGE=gpx-insight:latest` |
| `make clean` | Removes generated output files. | `make clean` |

### Docker image for AWS Lambda

Build the container image locally with:

```bash
make docker-build
```

The image includes the application modules, rendering assets, fonts, and dependencies. It does not declare a Lambda handler or `CMD`; a handler must be added before the image can be run as a Lambda function.

The CLI still defaults to writing `output/story.png`. The reusable service stages its input and intermediate images in a temporary directory, removes them on success or failure, and returns the final PNG as bytes. A future Lambda handler will still need to decide how to receive GPX bytes and return or persist the generated image.

### Reusable Python API

The application pipeline is also available without invoking the CLI:

```python
from service import generate_story

story_png = generate_story(gpx_bytes, theme="forest", lang="en")
```

`generate_story` accepts GPX content as bytes and returns PNG bytes. Supported themes are `forest`, `volcanic`, and `alpine`; supported languages are `en` and `es`.

### Output

GPX Insight generates a vertical PNG report containing:

- Route summary and elevation statistics.
- Elevation profile with key altitude points.
- Time, speed, and pace metrics.
- Gradient distribution and slope analysis.
- Uphill, downhill, and flat section statistics.

The report is rendered at a higher resolution and downscaled to **1080 × 1920 pixels** to improve visual quality.

### Run tests and validation

The project includes unit and integration tests to validate calculations and report generation.

```bash
make test
```

For an environment check before generating reports, run:

```bash
make check
```

The test suite covers distance calculations, elevation changes, timing, gradients, edge cases, and end-to-end report generation.

## Design Principles

GPX Insight follows three core principles:

- **Accuracy:** calculations should faithfully represent the information recorded in the GPX file.
- **Readability:** reports should be easy to understand and visually accessible on mobile devices.
- **Independence:** GPX analysis and report generation should run locally without requiring external services.

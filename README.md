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
| `make docker-build` | Builds the AWS Lambda Python 3.12 application image. | `make docker-build DOCKER_IMAGE=gpx-insight:latest` |
| `make floci-start` / `make floci-test` | Starts FloCI and checks its local endpoint. | `make floci-start && make floci-test` |
| `make floci-ecr-init` | Initializes the local ECR Terraform state. | `make floci-ecr-init` |
| `make floci-ecr-apply` | Creates the private `gpx-insight` repository in FloCI. | `make floci-ecr-apply` |
| `make floci-ecr-push` | Builds and publishes the image; defaults to tag `1.1.0`. | `make floci-ecr-push ECR_IMAGE_TAG=1.1.0` |
| `make floci-ecr-destroy` | Removes the repository managed by this Terraform state. | `make floci-ecr-destroy` |
| `make clean` | Removes generated output files. | `make clean` |

### Docker image for AWS Lambda

Build the container image locally with:

```bash
make docker-build
```

The image includes the application modules, rendering assets, fonts, and dependencies, and runs `handler.lambda_handler` using the AWS Lambda Python 3.12 runtime.

The CLI still defaults to writing `output/story.png`. The reusable service stages its input and intermediate images in a temporary directory, removes them on success or failure, and returns the final PNG as bytes.

### Local ECR lab with FloCI

Requirements: Docker, AWS CLI v2, Terraform 1.5+, and FloCI. The commands below use the local FloCI endpoint and fixed dummy credentials (`test`); the scripts disable AWS profile/config-file and metadata lookup. They do not use a real AWS account.

```bash
make floci-start
make floci-test
make floci-ecr-init
make floci-ecr-apply
make floci-ecr-push
```

`make floci-ecr-push` builds the configured local image (`DOCKER_IMAGE`, default `gpx-insight:latest`) and publishes it with tag `1.1.0`. Override the tag with `ECR_IMAGE_TAG=...`; override the local API endpoint via `FLOCI_ENDPOINT` or the existing FloCI `FLOCI_PORT` setting. Region defaults to the FloCI `.env` value (`eu-west-1`), and the Terraform outputs supply the exact registry URL and region used by the push script.

FloCI's ECR control-plane API uses the configured local endpoint (default `http://127.0.0.1:4566`). Its OCI Registry data plane returns an AWS-shaped hostname such as `<account>.dkr.ecr.<region>.localhost:4566`; this is distinct from the API host even though it uses the same port. Docker attempted HTTPS for that URI although this FloCI endpoint serves OCI over HTTP. FloCI's registry also accepts its path-style URL, so the push script maps the Terraform outputs to `localhost:4566/<account>/<region>/<repository>` without modifying the Terraform resource or global Docker settings. This path-style push was validated end-to-end. FloCI also documents a TLS hostname under `.localhost.floci.io`; TLS is not enabled on the locally published `4566` endpoint in this setup.

To clean up, run `make floci-ecr-destroy` (the local wrapper enables deletion of the repository and its pushed tags), then optionally `make floci-stop`. This Terraform root manages only this ECR repository; it creates no Lambda, API Gateway, or other AWS resources. FloCI emulates the service locally and is not a substitute for validating IAM, ECR policies, or registry behavior in AWS. The Terraform provider endpoint is configurable; leave `floci_endpoint` empty for the provider's AWS endpoint when using Terraform directly with appropriately configured real AWS credentials. Repository force deletion defaults off and is enabled only by the loopback-only FloCI wrapper. The `floci-ecr-*` targets are deliberately restricted to a loopback endpoint and dummy credentials.

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

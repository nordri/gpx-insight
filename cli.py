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
        metrics,
        theme=args.theme,
        lang=args.lang,
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
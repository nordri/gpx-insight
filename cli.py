import argparse
from pathlib import Path

from service import generate_story


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--input", required=True)
    parser.add_argument("--output", default="output/story.png")
    parser.add_argument("--theme", default="forest")
    parser.add_argument("--lang", default="en")

    args = parser.parse_args()

    story = generate_story(
        Path(args.input).read_bytes(),
        theme=args.theme,
        lang=args.lang,
    )
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(story)

    print(f"Story generated: {args.output}")


if __name__ == "__main__":
    main()
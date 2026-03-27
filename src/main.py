import argparse
import json
import re
import sys
from pathlib import Path

import anthropic
from pydantic import ValidationError

from src.generator import generate_implementation_plans
from src.models import TestDesignArtifact
from src.renderer import render_from_plans, render_playwright_skeleton


def _derive_output_path(requirement_title: str) -> Path:
    slug = re.sub(r"[^a-z0-9]+", "_", requirement_title.lower()).strip("_")
    return Path(f"{slug}.spec.ts")


def _load_artifact(input_path: Path) -> TestDesignArtifact:
    try:
        raw = json.loads(input_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[ERROR] Could not read input file: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        return TestDesignArtifact(**raw)
    except (ValidationError, TypeError) as exc:
        print(f"[ERROR] Input file failed schema validation:\n{exc}", file=sys.stderr)
        sys.exit(1)


def run(input_path: Path, output_path: Path | None) -> None:
    print(f"Loading artifact: {input_path}")
    artifact = _load_artifact(input_path)

    if output_path is None:
        output_path = _derive_output_path(artifact.requirement_title)

    print("Generating implementation plans...")

    try:
        client = anthropic.Anthropic()
        plans = generate_implementation_plans(artifact, client)
        output = render_from_plans(artifact, plans)
        render_mode = "AI-assisted"
    except (ValueError, anthropic.APIError) as exc:
        print(f"[WARN] AI generation failed: {exc}", file=sys.stderr)
        print("[WARN] Falling back to deterministic skeleton.", file=sys.stderr)
        output = render_playwright_skeleton(artifact)
        render_mode = "deterministic skeleton"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(output, encoding="utf-8")
    print(f"Written: {output_path} ({render_mode})")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a Playwright test skeleton from a test design artifact."
    )
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Path to the test design artifact JSON file.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=(
            "Path for the generated .spec.ts file. "
            "Defaults to <requirement_title>.spec.ts in the current directory."
        ),
    )
    args = parser.parse_args()
    run(args.input, args.output)


if __name__ == "__main__":
    main()

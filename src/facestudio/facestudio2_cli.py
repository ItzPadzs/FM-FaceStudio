from __future__ import annotations

import argparse
from pathlib import Path

from facestudio.facestudio2_pipeline import FaceStudio2Pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the FaceStudio 2.0 end-to-end portrait prototype")
    parser.add_argument("portrait", type=Path)
    parser.add_argument("--index", required=True, type=Path, help="donor-asset-index.json")
    parser.add_argument("--output", required=True, type=Path, help="output FM UV PNG")
    return parser


def main() -> int:
    args = build_parser().parse_args()

    def progress(percent: int, stage: str, preview: Path | None) -> None:
        suffix = f" [{preview}]" if preview else ""
        print(f"{percent:>3}% {stage}{suffix}")

    result = FaceStudio2Pipeline(args.index).run(args.portrait, args.output, progress)
    print(f"Donor: {result.donor.name} [{result.donor.donor_id}] {result.donor.score:.2f}%")
    print(f"Texture: {result.generation.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

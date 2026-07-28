from __future__ import annotations

import argparse
from pathlib import Path

from facestudio.donor_asset_index import DonorAssetIndexer, DonorMatcher


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Index FM donor assets and rank portrait matches")
    subparsers = parser.add_subparsers(dest="command", required=True)

    index = subparsers.add_parser("index", help="Build a donor asset index")
    index.add_argument("roots", nargs="+", type=Path, help="Asset-pack root folders")
    index.add_argument("--output", required=True, type=Path, help="Index output folder")
    index.add_argument("--names", type=Path, help="Optional CSV or JSON ID-to-name map")
    index.add_argument("--no-thumbnails", action="store_true", help="Skip face thumbnail files")

    match = subparsers.add_parser("match", help="Rank donors for one portrait")
    match.add_argument("portrait", type=Path)
    match.add_argument("--index", required=True, type=Path, help="donor-asset-index.json")
    match.add_argument("--limit", type=int, default=12)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "index":
        path = DonorAssetIndexer().build(
            args.roots,
            args.output,
            names_file=args.names,
            write_thumbnails=not args.no_thumbnails,
        )
        print(path)
        return 0

    matches = DonorMatcher(args.index).rank(args.portrait, limit=args.limit)
    for position, match in enumerate(matches, start=1):
        print(f"{position:>2}. {match.name} [{match.donor_id}] {match.score:.2f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

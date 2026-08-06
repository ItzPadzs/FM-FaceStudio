from __future__ import annotations

import argparse
from pathlib import Path

from facestudio.integrations.dylanfm_adapter import DylanFmAdapter


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Republish DylanFM Player Radar JSON output into the FM-FaceStudio bridge."
    )
    parser.add_argument("--fm-root", type=Path, help="Football Manager 26 installation folder")
    parser.add_argument(
        "--source-root",
        action="append",
        default=[],
        type=Path,
        help="Additional folder to search for active-player.json or ui-probe.json",
    )
    parser.add_argument("--once", action="store_true", help="Scan and publish once, then exit")
    args = parser.parse_args()

    adapter = DylanFmAdapter(fm_root=args.fm_root, extra_roots=args.source_root)
    if args.once:
        selection = adapter.publish_once()
        if selection is None:
            print("No valid DylanFM player output was found.")
            return 1
        print(f"Published {selection.name} ({selection.id})")
        return 0

    print(f"Watching DylanFM outputs; bridge folder: {adapter.bridge_root}")
    print("Press Ctrl+C to stop.")
    try:
        adapter.run()
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

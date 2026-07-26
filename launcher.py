from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    src = Path(__file__).resolve().parent / "src"
    sys.path.insert(0, str(src))
    from facestudio.app import main as run_app
    return run_app()


if __name__ == "__main__":
    raise SystemExit(main())

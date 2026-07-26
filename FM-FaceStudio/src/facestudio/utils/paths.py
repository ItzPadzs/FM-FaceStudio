from __future__ import annotations

import os
from pathlib import Path


def app_data_dir() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / "FM-FaceStudio"
    return Path.home() / ".fm-facestudio"

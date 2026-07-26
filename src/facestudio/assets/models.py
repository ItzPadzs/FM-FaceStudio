from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class AssetRecord:
    path: Path
    relative_path: str
    filename: str
    extension: str
    asset_type: str
    size_bytes: int
    modified_time: float

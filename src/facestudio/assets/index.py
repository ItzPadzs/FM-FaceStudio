from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class AssetRecord:
    asset_type: str
    path: Path
    size_bytes: int


class AssetIndex:
    def __init__(self) -> None:
        self._records: list[AssetRecord] = []

    @property
    def records(self) -> tuple[AssetRecord, ...]:
        return tuple(self._records)

    def clear(self) -> None:
        self._records.clear()

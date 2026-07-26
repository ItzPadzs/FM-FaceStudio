from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class FMInstallation:
    root: Path
    source: str

    @property
    def heads_dir(self) -> Path:
        return self.root / "heads"

    @property
    def is_valid(self) -> bool:
        return self.root.exists() and self.heads_dir.exists()


def candidates() -> tuple[FMInstallation, ...]:
    return (
        FMInstallation(Path(r"C:\Program Files (x86)\Steam\steamapps\common\Football Manager 26"), "Steam"),
        FMInstallation(Path(r"C:\Program Files\Steam\steamapps\common\Football Manager 26"), "Steam"),
        FMInstallation(Path(r"C:\XboxGames\Football Manager 26\Content"), "Xbox"),
    )


def detect_installation() -> FMInstallation | None:
    return next((item for item in candidates() if item.is_valid), None)

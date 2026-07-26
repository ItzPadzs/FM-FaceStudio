from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


PROJECT_FILENAME = "project.json"
PROJECT_SUFFIX = ".facestudio"


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


@dataclass(slots=True)
class FaceStudioProject:
    name: str = "Untitled Project"
    created_at: str = field(default_factory=utc_now_iso)
    modified_at: str = field(default_factory=utc_now_iso)
    source_photo: str = ""
    analysis_file: str = ""
    preview_file: str = ""
    selected_head: str = ""
    selected_hair: str = ""
    selected_beard: str = ""
    notes: str = ""
    app_version: str = "0.2.0-alpha.1"

    def touch(self) -> None:
        self.modified_at = utc_now_iso()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FaceStudioProject":
        allowed = {
            key: data[key]
            for key in cls.__dataclass_fields__
            if key in data
        }
        return cls(**allowed)

    def save_to_directory(self, directory: Path) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "generated").mkdir(exist_ok=True)
        self.touch()

        target = directory / PROJECT_FILENAME
        temporary = target.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(self.to_dict(), indent=2),
            encoding="utf-8",
        )
        temporary.replace(target)
        return target

    @classmethod
    def load_from_directory(cls, directory: Path) -> "FaceStudioProject":
        project_file = directory / PROJECT_FILENAME
        if not project_file.exists():
            raise FileNotFoundError(f"No {PROJECT_FILENAME} found in {directory}")
        payload = json.loads(project_file.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Project file must contain a JSON object.")
        return cls.from_dict(payload)

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(slots=True)
class FaceStudioProject:
    name: str = "Untitled Project"
    source_photo: str = ""
    selected_head: str = ""
    selected_hair: str = ""
    selected_beard: str = ""

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "FaceStudioProject":
        return cls(**json.loads(path.read_text(encoding="utf-8")))

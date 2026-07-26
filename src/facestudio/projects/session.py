from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from facestudio.projects.model import FaceStudioProject


@dataclass(slots=True)
class ProjectSession:
    project: FaceStudioProject | None = None
    directory: Path | None = None
    dirty: bool = False

    @property
    def is_open(self) -> bool:
        return self.project is not None and self.directory is not None

    def clear(self) -> None:
        self.project = None
        self.directory = None
        self.dirty = False

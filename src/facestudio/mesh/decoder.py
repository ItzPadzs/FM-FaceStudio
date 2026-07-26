from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class MeshSummary:
    source: Path
    kind: str
    vertex_count: int
    triangle_count: int


class SkinDecoder:
    def inspect(self, path: Path) -> MeshSummary:
        raise NotImplementedError("Decoder migration is planned for Alpha 0.3.")

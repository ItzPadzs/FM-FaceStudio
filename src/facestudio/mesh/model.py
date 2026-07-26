from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Vec3:
    x: float
    y: float
    z: float


@dataclass(frozen=True, slots=True)
class MeshData:
    source_path: Path
    vertices: tuple[Vec3, ...]
    edges: tuple[tuple[int, int], ...]
    faces: tuple[tuple[int, ...], ...]

    @property
    def vertex_count(self) -> int:
        return len(self.vertices)

    @property
    def edge_count(self) -> int:
        return len(self.edges)

    @property
    def face_count(self) -> int:
        return len(self.faces)

    def bounds(self) -> tuple[Vec3, Vec3]:
        if not self.vertices:
            zero = Vec3(0.0, 0.0, 0.0)
            return zero, zero
        return (
            Vec3(
                min(v.x for v in self.vertices),
                min(v.y for v in self.vertices),
                min(v.z for v in self.vertices),
            ),
            Vec3(
                max(v.x for v in self.vertices),
                max(v.y for v in self.vertices),
                max(v.z for v in self.vertices),
            ),
        )

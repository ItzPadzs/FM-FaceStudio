from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class HairDescriptor:
    """Scale-independent description of a hairstyle silhouette and structure."""

    vertex_count: int
    triangle_count: int
    component_count: int
    width_height_ratio: float
    depth_height_ratio: float
    width_depth_ratio: float
    centroid_y_ratio: float
    front_occupancy: tuple[int, ...]
    side_occupancy: tuple[int, ...]
    top_occupancy: tuple[int, ...]
    uv_outside_fraction: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["front_occupancy"] = list(self.front_occupancy)
        payload["side_occupancy"] = list(self.side_occupancy)
        payload["top_occupancy"] = list(self.top_occupancy)
        return payload


@dataclass(frozen=True, slots=True)
class HairAssetContract:
    """Files that belong to one native FM hair family.

    The paths are recorded, never normalised into fake aliases.  This is deliberate:
    _hair_nrm and _hair2_nrm are semantically different in the FM26 corpus.
    """

    uid: str
    root: Path
    skin: Path
    diffuse: Path | None
    normal: Path | None
    normal2: Path | None
    cfg2: Path | None

    @property
    def complete(self) -> bool:
        return self.skin.is_file() and self.diffuse is not None and self.diffuse.is_file()

    @property
    def normal_files(self) -> tuple[Path, ...]:
        return tuple(path for path in (self.normal, self.normal2) if path is not None)

    def to_dict(self) -> dict[str, Any]:
        return {
            "uid": self.uid,
            "root": str(self.root),
            "skin": str(self.skin),
            "diffuse": str(self.diffuse) if self.diffuse else None,
            "normal": str(self.normal) if self.normal else None,
            "normal2": str(self.normal2) if self.normal2 else None,
            "cfg2": str(self.cfg2) if self.cfg2 else None,
            "complete": self.complete,
        }


@dataclass(frozen=True, slots=True)
class HairCandidate:
    candidate_id: str
    display_name: str
    contract: HairAssetContract
    descriptor: HairDescriptor
    proven: bool = False
    family: str = "native-fm"
    notes: str = ""


@dataclass(frozen=True, slots=True)
class HairMatchResult:
    candidate: HairCandidate
    similarity: float
    base_similarity: float
    component_scores: dict[str, float]
    warnings: tuple[str, ...] = field(default_factory=tuple)

    @property
    def percentage(self) -> float:
        return 100.0 * self.similarity


@dataclass(frozen=True, slots=True)
class HairSelection:
    mode: str
    candidate_id: str | None
    source: str
    similarity: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

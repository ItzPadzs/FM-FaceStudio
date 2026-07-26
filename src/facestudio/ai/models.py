from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class Point:
    x: float
    y: float
    source: str
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class Rect:
    x: int
    y: int
    width: int
    height: int

    def to_dict(self) -> dict[str, int]:
        return asdict(self)


@dataclass(slots=True)
class FaceAnalysis:
    image_width: int
    image_height: int
    face_box: Rect
    landmarks: dict[str, Point] = field(default_factory=dict)
    measurements: dict[str, float] = field(default_factory=dict)
    face_shape: str = "undetermined"
    confidence: float = 0.0
    detector: str = "OpenCV Haar cascades"
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "image": {
                "width": self.image_width,
                "height": self.image_height,
            },
            "face_box": self.face_box.to_dict(),
            "landmarks": {
                name: point.to_dict()
                for name, point in self.landmarks.items()
            },
            "measurements": self.measurements,
            "face_shape": self.face_shape,
            "confidence": self.confidence,
            "detector": self.detector,
            "notes": self.notes,
        }

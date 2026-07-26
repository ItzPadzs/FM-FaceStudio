from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class FaceDescriptor:
    face_height_width_ratio: float
    inter_eye_face_width_ratio: float
    eye_line_face_height_ratio: float
    mouth_line_face_height_ratio: float
    face_shape: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_analysis_payload(cls, payload: dict[str, Any]) -> "FaceDescriptor":
        measurements = payload.get("measurements", {})
        return cls(
            face_height_width_ratio=float(
                measurements["face_height_width_ratio"]
            ),
            inter_eye_face_width_ratio=float(
                measurements["inter_eye_face_width_ratio"]
            ),
            eye_line_face_height_ratio=float(
                measurements["eye_line_face_height_ratio"]
            ),
            mouth_line_face_height_ratio=float(
                measurements["mouth_line_face_height_ratio"]
            ),
            face_shape=str(payload.get("face_shape", "undetermined")),
        )


@dataclass(frozen=True, slots=True)
class MatchCandidate:
    candidate_id: str
    display_name: str
    descriptor: FaceDescriptor
    source: str = "sample catalogue"
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "display_name": self.display_name,
            "descriptor": self.descriptor.to_dict(),
            "source": self.source,
            "notes": self.notes,
        }


@dataclass(frozen=True, slots=True)
class MatchResult:
    candidate: MatchCandidate
    similarity: float
    distance: float
    component_scores: dict[str, float]

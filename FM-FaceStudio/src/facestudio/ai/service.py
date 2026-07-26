from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class FaceDescriptor:
    source_image: Path
    face_width_to_height: float
    eye_distance_to_face_width: float
    mouth_width_to_face_width: float
    nose_width_to_face_width: float
    skin_hex: str


class FaceAnalysisService:
    def analyse(self, image_path: Path) -> FaceDescriptor:
        raise NotImplementedError("Face AI migration is planned for Alpha 0.5.")

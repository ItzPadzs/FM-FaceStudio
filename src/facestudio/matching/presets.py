from __future__ import annotations

import json
from pathlib import Path

from facestudio.matching.models import FaceDescriptor


class DescriptorPresetStore:
    def save(self, descriptor: FaceDescriptor, path: Path) -> Path:
        payload = {
            "schema_version": 1,
            "descriptor": descriptor.to_dict(),
        }
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        temporary.replace(path)
        return path

    def load(self, path: Path) -> FaceDescriptor:
        payload = json.loads(path.read_text(encoding="utf-8"))
        descriptor = payload.get("descriptor", payload)
        return FaceDescriptor(
            face_height_width_ratio=float(
                descriptor["face_height_width_ratio"]
            ),
            inter_eye_face_width_ratio=float(
                descriptor["inter_eye_face_width_ratio"]
            ),
            eye_line_face_height_ratio=float(
                descriptor["eye_line_face_height_ratio"]
            ),
            mouth_line_face_height_ratio=float(
                descriptor["mouth_line_face_height_ratio"]
            ),
            face_shape=str(descriptor.get("face_shape", "undetermined")),
        )

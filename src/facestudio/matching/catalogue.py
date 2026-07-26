from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from facestudio.matching.models import FaceDescriptor, MatchCandidate


class CandidateCatalogue:
    def load(self, path: Path) -> list[MatchCandidate]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError("Candidate catalogue must contain a JSON list.")

        candidates: list[MatchCandidate] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            descriptor_payload = item.get("descriptor")
            if not isinstance(descriptor_payload, dict):
                continue
            candidates.append(
                MatchCandidate(
                    candidate_id=str(item["candidate_id"]),
                    display_name=str(item["display_name"]),
                    descriptor=FaceDescriptor(
                        face_height_width_ratio=float(
                            descriptor_payload["face_height_width_ratio"]
                        ),
                        inter_eye_face_width_ratio=float(
                            descriptor_payload["inter_eye_face_width_ratio"]
                        ),
                        eye_line_face_height_ratio=float(
                            descriptor_payload["eye_line_face_height_ratio"]
                        ),
                        mouth_line_face_height_ratio=float(
                            descriptor_payload["mouth_line_face_height_ratio"]
                        ),
                        face_shape=str(
                            descriptor_payload.get(
                                "face_shape",
                                "undetermined",
                            )
                        ),
                    ),
                    source=str(item.get("source", "sample catalogue")),
                    notes=str(item.get("notes", "")),
                )
            )
        return candidates

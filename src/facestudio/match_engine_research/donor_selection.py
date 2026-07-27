from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path

from facestudio.match_engine_research.geometry_dataset import GeometryMatch, HeadGeometryRecord
from facestudio.match_engine_research.one_click_face_builder import FaceMeasurements


SELECTION_FORMAT = "facestudio-donor-selection-v1"


@dataclass(frozen=True)
class LockedDonor:
    player_id: str
    score: int
    source_type: str
    confidence: float
    front_render: str | None
    side_render: str | None
    component_differences: dict[str, float]
    portrait_measurements: FaceMeasurements


class DonorSelectionService:
    """Review, lock and export one evidence-backed donor choice."""

    @staticmethod
    def record_for_match(match: GeometryMatch, records: tuple[HeadGeometryRecord, ...]) -> HeadGeometryRecord:
        for record in records:
            if record.player_id == match.player_id:
                return record
        raise ValueError(f"Geometry record not found for donor {match.player_id}.")

    @staticmethod
    def lock(match: GeometryMatch, portrait: FaceMeasurements) -> LockedDonor:
        if match.score <= 0:
            raise ValueError("A zero-score geometry match cannot be locked.")
        return LockedDonor(
            player_id=match.player_id,
            score=match.score,
            source_type=match.source_type,
            confidence=match.confidence,
            front_render=match.front_render,
            side_render=match.side_render,
            component_differences=dict(match.component_differences),
            portrait_measurements=portrait,
        )

    @staticmethod
    def save(selection: LockedDonor, destination: Path) -> Path:
        destination = destination.with_suffix(".json")
        payload = {
            "format": SELECTION_FORMAT,
            "selected_donor": {
                "player_id": selection.player_id,
                "score": selection.score,
                "source_type": selection.source_type,
                "confidence": selection.confidence,
                "front_render": selection.front_render,
                "side_render": selection.side_render,
                "component_differences": selection.component_differences,
            },
            "portrait_measurements": asdict(selection.portrait_measurements),
            "next_stage": "landmark-driven-texture-reconstruction",
        }
        destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return destination

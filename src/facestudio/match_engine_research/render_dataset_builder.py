from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from facestudio.match_engine_research.geometry_dataset import GeometryDatasetService, HeadGeometryRecord
from facestudio.match_engine_research.one_click_face_builder import OneClickFaceBuilder, PhotoAnalysis


_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
_ID_PATTERN = re.compile(r"^(?P<id>\d+)(?:[_-](?:front|frontal|head))?$")


@dataclass(frozen=True)
class RenderCandidate:
    player_id: str
    front_render: str


class RenderDatasetBuilder:
    """Build calibrated FM geometry records from standardised front renders.

    The service intentionally accepts only a separate render folder whose files use
    numeric player IDs. Loose FM UV textures must not be supplied here because they
    are not frontal geometry evidence.
    """

    def __init__(self) -> None:
        self.face_service = OneClickFaceBuilder()
        self.dataset_service = GeometryDatasetService()

    def scan(self, folder: Path) -> tuple[RenderCandidate, ...]:
        folder = folder.expanduser()
        if not folder.is_dir():
            raise ValueError(f"Render folder not found: {folder}")
        candidates: list[RenderCandidate] = []
        seen: set[str] = set()
        for path in sorted(folder.iterdir(), key=lambda item: item.name.lower()):
            if not path.is_file() or path.suffix.lower() not in _IMAGE_SUFFIXES:
                continue
            match = _ID_PATTERN.match(path.stem.lower())
            if not match:
                continue
            player_id = match.group("id")
            if player_id in seen:
                raise ValueError(f"Duplicate front render for player ID {player_id}.")
            seen.add(player_id)
            candidates.append(RenderCandidate(player_id=player_id, front_render=str(path.resolve())))
        if not candidates:
            raise ValueError(
                "No calibrated front renders were found. Use numeric names such as 55041632.png or 55041632_front.png."
            )
        return tuple(candidates)

    def analyse(self, candidate: RenderCandidate) -> PhotoAnalysis:
        return self.face_service.analyse_photo(Path(candidate.front_render))

    def move_landmark(self, analysis: PhotoAnalysis, name: str, x: float, y: float) -> PhotoAnalysis:
        return self.face_service.update_landmark(analysis, name, x, y)

    @staticmethod
    def make_record(candidate: RenderCandidate, analysis: PhotoAnalysis, confidence: float = 0.90) -> HeadGeometryRecord:
        if not analysis.manually_corrected:
            raise ValueError("Correct at least one landmark before accepting this render record.")
        confidence = max(0.0, min(1.0, float(confidence)))
        return HeadGeometryRecord(
            player_id=candidate.player_id,
            measurements=analysis.measurements,
            source_type="calibrated-render",
            confidence=confidence,
            front_render=candidate.front_render,
            notes="Created in FaceStudio Render Dataset Builder from a manually reviewed standard front render.",
        )

    def save(self, records: tuple[HeadGeometryRecord, ...], destination: Path) -> Path:
        if not records:
            raise ValueError("No calibrated render records have been accepted.")
        ids = [record.player_id for record in records]
        if len(ids) != len(set(ids)):
            raise ValueError("The dataset contains duplicate player IDs.")
        return self.dataset_service.save_dataset(records, destination)

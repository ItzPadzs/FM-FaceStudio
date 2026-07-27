from __future__ import annotations

import json
from pathlib import Path

import pytest

from facestudio.match_engine_research.donor_selection import DonorSelectionService, SELECTION_FORMAT
from facestudio.match_engine_research.geometry_dataset import GeometryMatch, HeadGeometryRecord
from facestudio.match_engine_research.one_click_face_builder import FaceMeasurements


def _measurements() -> FaceMeasurements:
    return FaceMeasurements(
        face_width=0.38,
        face_height=0.66,
        eye_spacing=0.18,
        nose_length=0.14,
        mouth_width=0.14,
        jaw_width=0.30,
        chin_length=0.25,
        symmetry=0.98,
    )


def _match(score: int = 91) -> GeometryMatch:
    return GeometryMatch(
        player_id="55041632",
        score=score,
        distance=0.04,
        confidence=0.92,
        source_type="calibrated-render",
        front_render="front.png",
        side_render="side.png",
        component_differences={"face_width": 0.01, "jaw_width": 0.02},
    )


def test_lock_preserves_reviewed_match_and_portrait_measurements() -> None:
    locked = DonorSelectionService.lock(_match(), _measurements())

    assert locked.player_id == "55041632"
    assert locked.score == 91
    assert locked.portrait_measurements.face_width == pytest.approx(0.38)
    assert locked.component_differences["jaw_width"] == pytest.approx(0.02)


def test_zero_score_match_cannot_be_locked() -> None:
    with pytest.raises(ValueError, match="zero-score"):
        DonorSelectionService.lock(_match(score=0), _measurements())


def test_record_for_match_finds_matching_dataset_record() -> None:
    record = HeadGeometryRecord(
        player_id="55041632",
        measurements=_measurements(),
        source_type="calibrated-render",
        confidence=0.92,
    )

    found = DonorSelectionService.record_for_match(_match(), (record,))

    assert found is record


def test_record_for_match_rejects_missing_record() -> None:
    with pytest.raises(ValueError, match="not found"):
        DonorSelectionService.record_for_match(_match(), ())


def test_locked_donor_manifest_is_versioned_and_ready_for_next_stage(tmp_path: Path) -> None:
    locked = DonorSelectionService.lock(_match(), _measurements())

    destination = DonorSelectionService.save(locked, tmp_path / "selection")
    payload = json.loads(destination.read_text(encoding="utf-8"))

    assert payload["format"] == SELECTION_FORMAT
    assert payload["selected_donor"]["player_id"] == "55041632"
    assert payload["portrait_measurements"]["eye_spacing"] == pytest.approx(0.18)
    assert payload["next_stage"] == "landmark-driven-texture-reconstruction"

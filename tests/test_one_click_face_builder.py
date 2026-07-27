from __future__ import annotations

import json
from pathlib import Path

import pytest
from PySide6.QtGui import QImage

from facestudio.match_engine_research.one_click_face_builder import LANDMARK_ORDER, OneClickFaceBuilder


def _write_png(path: Path, colour: int, width: int = 1024, height: int = 1024) -> None:
    image = QImage(width, height, QImage.Format.Format_ARGB32)
    image.fill(colour)
    assert image.save(str(path), "PNG")


def _asset_set(root: Path, player_id: str) -> None:
    (root / f"{player_id}.skin").write_bytes(b"SKIN")
    _write_png(root / f"{player_id}.png", 0xFF8C604A)
    (root / f"{player_id}.cfg2").write_text("eye_l=0,0,0\n", encoding="utf-8")


def test_photo_analysis_returns_named_estimated_landmarks(tmp_path: Path) -> None:
    photo = tmp_path / "photo.png"
    _write_png(photo, 0xFF8C604A)

    analysis = OneClickFaceBuilder().analyse_photo(photo)

    assert analysis.annotated_preview.size() == QImage(str(photo)).size()
    assert tuple(point.name for point in analysis.landmarks) == LANDMARK_ORDER
    assert all(0.0 <= point.x <= 1.0 and 0.0 <= point.y <= 1.0 for point in analysis.landmarks)
    assert all(point.confidence < 0.5 for point in analysis.landmarks)
    assert not analysis.manually_corrected
    assert any("estimates" in warning for warning in analysis.warnings)


def test_manual_landmark_correction_recalculates_measurements(tmp_path: Path) -> None:
    photo = tmp_path / "photo.png"
    _write_png(photo, 0xFF8C604A)
    service = OneClickFaceBuilder()
    analysis = service.analyse_photo(photo)
    original_width = analysis.measurements.face_width

    corrected = service.update_landmark(analysis, "left_temple", 0.20, 0.30)

    point = next(item for item in corrected.landmarks if item.name == "left_temple")
    assert point.x == pytest.approx(0.20)
    assert point.confidence == 1.0
    assert corrected.manually_corrected
    assert corrected.measurements.face_width > original_width


def test_landmark_coordinates_are_clamped(tmp_path: Path) -> None:
    photo = tmp_path / "photo.png"
    _write_png(photo, 0xFF8C604A)
    service = OneClickFaceBuilder()
    analysis = service.analyse_photo(photo)

    corrected = service.update_landmark(analysis, "chin", 2.0, -1.0)
    point = next(item for item in corrected.landmarks if item.name == "chin")

    assert point.x == 1.0
    assert point.y == 0.0


def test_unknown_landmark_is_rejected(tmp_path: Path) -> None:
    photo = tmp_path / "photo.png"
    _write_png(photo, 0xFF8C604A)
    service = OneClickFaceBuilder()
    analysis = service.analyse_photo(photo)

    with pytest.raises(ValueError, match="Unknown landmark"):
        service.update_landmark(analysis, "left_ear_tip", 0.1, 0.2)


def test_analysis_json_is_transparent_and_versioned(tmp_path: Path) -> None:
    photo = tmp_path / "photo.png"
    _write_png(photo, 0xFF8C604A)
    service = OneClickFaceBuilder()
    analysis = service.update_landmark(service.analyse_photo(photo), "nose_tip", 0.51, 0.58)

    destination = service.save_analysis(analysis, tmp_path / "record")
    payload = json.loads(destination.read_text(encoding="utf-8"))

    assert payload["format"] == "facestudio-landmarks-v1"
    assert payload["manually_corrected"] is True
    assert len(payload["landmarks"]) == len(LANDMARK_ORDER)
    assert "measurements" in payload


def test_library_index_reports_zero_comparable_geometry_records(tmp_path: Path) -> None:
    _asset_set(tmp_path, "100")
    _asset_set(tmp_path, "200")

    result = OneClickFaceBuilder().index_library(tmp_path)

    assert result.head_sets == 2
    assert result.textures == 2
    assert result.cfg2_files == 2
    assert result.geometry_records == 0
    assert any("Donor ranking remains disabled" in warning for warning in result.warnings)


def test_missing_photo_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Image not found"):
        OneClickFaceBuilder().analyse_photo(tmp_path / "missing.png")

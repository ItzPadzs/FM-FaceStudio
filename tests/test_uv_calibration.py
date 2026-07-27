from __future__ import annotations

import json
from pathlib import Path

import pytest
from PySide6.QtGui import QImage

from facestudio.match_engine_research.one_click_face_builder import LANDMARK_ORDER
from facestudio.match_engine_research.uv_calibration import UVCalibrationService


def _png(path: Path) -> None:
    image = QImage(1024, 1024, QImage.Format.Format_ARGB32)
    image.fill(0xFF806050)
    assert image.save(str(path), "PNG")


def test_locates_numeric_donor_texture_recursively(tmp_path: Path) -> None:
    nested = tmp_path / "heads"; nested.mkdir()
    _png(nested / "123.png")
    assert UVCalibrationService.locate_texture(tmp_path, "123").name == "123.png"


def test_create_returns_all_low_confidence_uv_anchors(tmp_path: Path) -> None:
    _png(tmp_path / "123.png")
    calibration = UVCalibrationService().create(tmp_path, "123")
    assert tuple(item.name for item in calibration.anchors) == LANDMARK_ORDER
    assert all(item.confidence < 0.5 for item in calibration.anchors)
    assert not calibration.complete


def test_drag_updates_and_clamps_anchor(tmp_path: Path) -> None:
    _png(tmp_path / "123.png")
    service = UVCalibrationService()
    calibration = service.create(tmp_path, "123")
    updated = service.update(calibration, "nose_tip", 2.0, -1.0)
    point = next(item for item in updated.anchors if item.name == "nose_tip")
    assert point.x == 1.0 and point.y == 0.0
    assert point.confidence == 1.0
    assert "nose_tip" in updated.corrected_names


def test_save_requires_review_and_writes_versioned_plan(tmp_path: Path) -> None:
    _png(tmp_path / "123.png")
    service = UVCalibrationService()
    calibration = service.create(tmp_path, "123")
    with pytest.raises(ValueError, match="Move at least one"):
        service.save(calibration, tmp_path / "uv")
    calibration = service.update(calibration, "left_eye", 0.2, 0.3)
    destination = service.save(calibration, tmp_path / "uv")
    payload = json.loads(destination.read_text(encoding="utf-8"))
    assert payload["format"] == "facestudio-donor-uv-calibration-v1"
    assert payload["player_id"] == "123"
    assert payload["next_stage"] == "triangulated-landmark-texture-warp"

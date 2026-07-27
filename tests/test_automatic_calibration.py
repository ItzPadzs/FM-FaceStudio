from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtGui import QImage

from facestudio.match_engine_research.automatic_calibration import (
    AutomaticCalibrationService,
    DEFAULT_UV_ANCHORS,
    GEOMETRY_FORMAT,
    UV_FORMAT,
)
from facestudio.match_engine_research.one_click_face_builder import LANDMARK_ORDER


def _image(path: Path) -> None:
    image = QImage(640, 640, QImage.Format.Format_ARGB32)
    image.fill(0xffb99578)
    assert image.save(str(path), "PNG")


def test_auto_geometry_is_editable(tmp_path: Path) -> None:
    photo = tmp_path / "portrait.png"
    _image(photo)
    analysis, portrait, geometry = AutomaticCalibrationService().calibrate_geometry(photo, tmp_path)
    payload = json.loads(geometry.read_text(encoding="utf-8"))
    assert payload["format"] == GEOMETRY_FORMAT
    assert payload["fine_tunable"] is True
    assert len(payload["landmarks"]) == len(LANDMARK_ORDER)
    AutomaticCalibrationService.update_geometry(geometry, {"chin": (0.51, 0.91)})
    updated = json.loads(geometry.read_text(encoding="utf-8"))
    assert updated["review_state"] == "fine-tuned"
    assert updated["confidence"] == 1.0
    portrait_payload = json.loads(portrait.read_text(encoding="utf-8"))
    assert portrait_payload["manually_corrected"] is True


def test_auto_uv_profile_is_complete_and_editable(tmp_path: Path) -> None:
    texture = tmp_path / "12345.png"
    _image(texture)
    profile = AutomaticCalibrationService().create_uv_profile("12345", texture, tmp_path / "profiles")
    payload = json.loads(profile.read_text(encoding="utf-8"))
    assert payload["format"] == UV_FORMAT
    assert payload["complete"] is True
    assert payload["review_state"] == "provisional-auto-estimate"
    assert {item["name"] for item in payload["anchors"]} == set(LANDMARK_ORDER)
    AutomaticCalibrationService.update_uv(profile, {"nose_tip": (0.49, 0.57)})
    updated = json.loads(profile.read_text(encoding="utf-8"))
    assert updated["review_state"] == "fine-tuned"
    assert "nose_tip" in updated["corrected_anchors"]


def test_find_numeric_donor_texture(tmp_path: Path) -> None:
    texture = tmp_path / "nested" / "9876.png"
    texture.parent.mkdir()
    _image(texture)
    assert AutomaticCalibrationService.find_donor_texture(tmp_path, "9876") == texture

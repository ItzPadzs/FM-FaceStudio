from __future__ import annotations

import json
from pathlib import Path

import pytest
from PySide6.QtGui import QImage

from facestudio.match_engine_research.one_click_face_builder import LANDMARK_ORDER
from facestudio.match_engine_research.texture_reconstruction import TextureReconstructionService


def _image(path: Path, colour: int, size: int = 64) -> None:
    image = QImage(size, size, QImage.Format.Format_ARGB32); image.fill(colour); assert image.save(str(path), "PNG")


def _points() -> list[dict]:
    defaults = {
        "face_top": (.50,.12), "left_temple": (.25,.28), "right_temple": (.75,.28),
        "left_eye": (.38,.40), "right_eye": (.62,.40), "nose_bridge": (.50,.43),
        "nose_tip": (.50,.57), "left_mouth": (.42,.67), "right_mouth": (.58,.67),
        "left_jaw": (.30,.76), "right_jaw": (.70,.76), "chin": (.50,.88),
    }
    return [{"name": name, "x": defaults[name][0], "y": defaults[name][1], "confidence": 1.0} for name in LANDMARK_ORDER]


def _records(tmp_path: Path, complete: bool = True) -> tuple[Path, Path]:
    portrait = tmp_path / "portrait.png"; donor = tmp_path / "123.png"
    _image(portrait, 0xFFD09A7A); _image(donor, 0xFF705044)
    portrait_json = tmp_path / "portrait.json"
    portrait_json.write_text(json.dumps({"format":"facestudio-landmarks-v1","source_path":str(portrait),"landmarks":_points()}), encoding="utf-8")
    uv_json = tmp_path / "uv.json"
    uv_json.write_text(json.dumps({"format":"facestudio-donor-uv-calibration-v1","player_id":"123","texture_path":str(donor),"complete":complete,"anchors":_points()}), encoding="utf-8")
    return portrait_json, uv_json


def test_reconstruction_transfers_reviewed_triangles(tmp_path: Path) -> None:
    portrait, uv = _records(tmp_path)
    result = TextureReconstructionService().reconstruct(portrait, uv)
    assert result.player_id == "123"
    assert result.triangles_written > 0
    assert result.pixels_written > 0
    assert result.output.size() == QImage(result.donor_texture).size()


def test_incomplete_uv_record_is_rejected(tmp_path: Path) -> None:
    portrait, uv = _records(tmp_path, complete=False)
    with pytest.raises(ValueError, match="incomplete"):
        TextureReconstructionService().reconstruct(portrait, uv)


def test_export_writes_png_and_manifest(tmp_path: Path) -> None:
    portrait, uv = _records(tmp_path)
    service = TextureReconstructionService(); result = service.reconstruct(portrait, uv)
    png, manifest = service.save(result, tmp_path / "output")
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert png.is_file()
    assert payload["format"] == "facestudio-texture-reconstruction-v1"
    assert payload["next_stage"] == "seam-blending-and-game-preview"

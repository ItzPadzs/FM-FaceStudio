from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtGui import QImage

from facestudio.match_engine_research.mesh_head_studio import MeshHeadStudioService


def _write_png(path: Path, width: int = 1024, height: int = 1024) -> None:
    image = QImage(width, height, QImage.Format.Format_ARGB32)
    image.fill(0xFF8A6F5D)
    assert image.save(str(path), "PNG")


def test_photo_assessment_reports_dimensions(tmp_path: Path) -> None:
    photo = tmp_path / "portrait.png"
    _write_png(photo, 1200, 1400)
    result = MeshHeadStudioService().assess_photo(photo)
    assert result.width == 1200
    assert result.height == 1400
    assert result.quality == "Good"


def test_obj_is_recognised_as_external_preview_mesh(tmp_path: Path) -> None:
    obj = tmp_path / "head.obj"
    obj.write_text("v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n", encoding="utf-8")
    result = MeshHeadStudioService().assess_mesh_source(obj)
    assert result.source_type == "Wavefront OBJ"
    assert result.usable_for_preview is True


def test_skin_remains_research_only(tmp_path: Path) -> None:
    skin = tmp_path / "head.skin"
    skin.write_bytes(b"SKIN\x00\x01")
    result = MeshHeadStudioService().assess_mesh_source(skin)
    assert result.source_type == "FM26 SKIN research file"
    assert result.usable_for_preview is False


def test_head_preview_uses_existing_photo_pipeline(tmp_path: Path) -> None:
    photo = tmp_path / "portrait.png"
    _write_png(photo)
    result = MeshHeadStudioService().build_head_preview(photo, yaw=20, depth_strength=60)
    assert result.preview.width() == 560
    assert result.preview.height() == 560
    assert result.yaw == 20


def test_missing_photo_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Image not found"):
        MeshHeadStudioService().assess_photo(tmp_path / "missing.png")

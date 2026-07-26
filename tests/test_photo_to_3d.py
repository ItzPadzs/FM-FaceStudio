from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtGui import QColor, QImage

from facestudio.match_engine_research.photo_to_3d import PhotoTo3DService


def _save_image(path: Path, width: int = 320, height: int = 420) -> None:
    image = QImage(width, height, QImage.Format.Format_ARGB32)
    image.fill(QColor(180, 130, 100))
    assert image.save(str(path), "PNG")


def test_preview_is_created_with_requested_settings(tmp_path: Path) -> None:
    photo = tmp_path / "photo.png"
    _save_image(photo)

    result = PhotoTo3DService().create_preview(photo, yaw=35, depth_strength=70, size=360)

    assert result.preview.width() == 360
    assert result.preview.height() == 360
    assert result.yaw == 35
    assert result.depth_strength == 70
    assert result.source_width == 320
    assert result.source_height == 420


def test_preview_clamps_rotation_and_depth(tmp_path: Path) -> None:
    photo = tmp_path / "photo.png"
    _save_image(photo)

    result = PhotoTo3DService().create_preview(photo, yaw=200, depth_strength=-10)

    assert result.yaw == 65
    assert result.depth_strength == 0


def test_preview_rejects_missing_photo(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Image not found"):
        PhotoTo3DService().create_preview(tmp_path / "missing.png")


def test_texture_transfer_uses_existing_template(tmp_path: Path) -> None:
    photo = tmp_path / "photo.png"
    template = tmp_path / "123.png"
    _save_image(photo)
    _save_image(template, 512, 512)

    result = PhotoTo3DService().transfer_to_template("123", photo, template)

    assert result.texture.width() == 512
    assert result.texture.height() == 512
    assert result.confidence > 0

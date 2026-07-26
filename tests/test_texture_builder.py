from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtGui import QColor, QImage

from facestudio.match_engine_research.texture_builder import PhotoTextureBuilder


def _write_image(path: Path, width: int, height: int, color: str) -> None:
    image = QImage(width, height, QImage.Format.Format_ARGB32)
    image.fill(QColor(color))
    assert image.save(str(path), "PNG")


def test_build_creates_separate_png_with_template_dimensions(tmp_path: Path) -> None:
    photo = tmp_path / "photo.png"
    template = tmp_path / "template.png"
    destination = tmp_path / "output.png"
    _write_image(photo, 400, 600, "#bb7755")
    _write_image(template, 1024, 1024, "#553322")

    result = PhotoTextureBuilder().build("2000382120", photo, template, destination)

    assert destination.is_file()
    output = QImage(str(destination))
    assert output.size() == QImage(str(template)).size()
    assert result.player_id == "2000382120"
    assert result.width == 1024
    assert result.height == 1024
    assert photo.is_file()
    assert template.is_file()


def test_build_rejects_non_numeric_unique_id(tmp_path: Path) -> None:
    photo = tmp_path / "photo.png"
    template = tmp_path / "template.png"
    _write_image(photo, 100, 100, "#ffffff")
    _write_image(template, 100, 100, "#000000")

    with pytest.raises(ValueError, match="digits only"):
        PhotoTextureBuilder().build("player-1", photo, template, tmp_path / "output.png")


def test_build_rejects_missing_source_files(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="source photograph"):
        PhotoTextureBuilder().build(
            "123",
            tmp_path / "missing-photo.png",
            tmp_path / "missing-template.png",
            tmp_path / "output.png",
        )

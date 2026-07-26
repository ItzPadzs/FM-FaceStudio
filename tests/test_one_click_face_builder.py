from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtGui import QImage

from facestudio.match_engine_research.one_click_face_builder import OneClickFaceBuilder


def _write_png(path: Path, colour: int, width: int = 1024, height: int = 1024) -> None:
    image = QImage(width, height, QImage.Format.Format_ARGB32)
    image.fill(colour)
    assert image.save(str(path), "PNG")


def _asset_set(root: Path, player_id: str, colour: int, complete: bool = True) -> None:
    (root / f"{player_id}.skin").write_bytes(b"SKIN")
    _write_png(root / f"{player_id}.png", colour)
    if complete:
        (root / f"{player_id}.cfg2").write_text("eye_l=0,0,0\n", encoding="utf-8")
        (root / f"{player_id}_hair.skin").write_bytes(b"HAIR")


def test_builder_selects_closest_complete_template(tmp_path: Path) -> None:
    photo = tmp_path / "photo.png"
    _write_png(photo, 0xFF8C604A)
    _asset_set(tmp_path, "100", 0xFF8A5F49, complete=True)
    _asset_set(tmp_path, "200", 0xFFD7B59A, complete=True)

    result = OneClickFaceBuilder().build(photo, tmp_path)

    assert result.player_id == "100"
    assert result.library_count >= 2
    assert result.texture.width() == 1024
    assert result.texture.height() == 1024


def test_builder_prefers_complete_asset_set_when_colours_are_close(tmp_path: Path) -> None:
    photo = tmp_path / "photo.png"
    _write_png(photo, 0xFF9A7058)
    _asset_set(tmp_path, "100", 0xFF997058, complete=False)
    _asset_set(tmp_path, "200", 0xFF9E745C, complete=True)

    result = OneClickFaceBuilder().build(photo, tmp_path)

    assert result.player_id == "200"


def test_builder_rejects_library_without_face_templates(tmp_path: Path) -> None:
    photo = tmp_path / "photo.png"
    _write_png(photo, 0xFF8C604A)
    (tmp_path / "100.skin").write_bytes(b"SKIN")

    with pytest.raises(ValueError, match="No complete FM26 face template"):
        OneClickFaceBuilder().build(photo, tmp_path)


def test_builder_rejects_missing_photo(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Image not found"):
        OneClickFaceBuilder().build(tmp_path / "missing.png", tmp_path)

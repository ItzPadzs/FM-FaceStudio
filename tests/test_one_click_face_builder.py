from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtGui import QImage, QColor

from facestudio.match_engine_research.one_click_face_builder import OneClickFaceBuilder


def _write_png(path: Path, colour: int, width: int = 1024, height: int = 1024) -> None:
    image = QImage(width, height, QImage.Format.Format_ARGB32)
    image.fill(colour)
    assert image.save(str(path), "PNG")


def _write_structured_face(path: Path, base: int, wide_jaw: bool = False) -> None:
    image = QImage(1024, 1024, QImage.Format.Format_ARGB32)
    image.fill(base)
    dark = QColor(45, 35, 30)
    jaw_start = 190 if wide_jaw else 290
    jaw_end = 834 if wide_jaw else 734
    for x in range(260, 764):
        for y in range(305, 326):
            image.setPixelColor(x, y, dark)
    for x in range(430, 594):
        for y in range(420, 620):
            image.setPixelColor(x, y, dark)
    for x in range(345, 679):
        for y in range(660, 690):
            image.setPixelColor(x, y, dark)
    for x in range(jaw_start, jaw_end):
        for y in range(760, 795):
            image.setPixelColor(x, y, dark)
    assert image.save(str(path), "PNG")


def _asset_set(root: Path, player_id: str, colour: int, complete: bool = True, wide_jaw: bool | None = None) -> None:
    (root / f"{player_id}.skin").write_bytes(b"SKIN")
    if wide_jaw is None:
        _write_png(root / f"{player_id}.png", colour)
    else:
        _write_structured_face(root / f"{player_id}.png", colour, wide_jaw)
    if complete:
        (root / f"{player_id}.cfg2").write_text("eye_l=0,0,0\n", encoding="utf-8")
        (root / f"{player_id}_hair.skin").write_bytes(b"HAIR")


def test_photo_analysis_returns_overlay_and_quality_scores(tmp_path: Path) -> None:
    photo = tmp_path / "photo.png"
    _write_structured_face(photo, 0xFF8C604A, wide_jaw=True)

    analysis = OneClickFaceBuilder().analyse_photo(photo)

    assert analysis.annotated_preview.width() == 1024
    assert analysis.annotated_preview.height() == 1024
    assert 0 <= analysis.quality_score <= 100
    assert 0 <= analysis.lighting_score <= 100
    assert 0 <= analysis.sharpness_score <= 100
    assert 0 <= analysis.frontal_score <= 100


def test_builder_returns_ranked_geometry_matches_and_preserves_template_size(tmp_path: Path) -> None:
    photo = tmp_path / "photo.png"
    _write_structured_face(photo, 0xFF8C604A, wide_jaw=True)
    _asset_set(tmp_path, "100", 0xFF8A5F49, complete=True, wide_jaw=True)
    _asset_set(tmp_path, "200", 0xFFD7B59A, complete=True, wide_jaw=False)

    result = OneClickFaceBuilder().build(photo, tmp_path)

    assert result.player_id == "100"
    assert result.library_count >= 2
    assert result.texture.width() == 1024
    assert result.texture.height() == 1024
    assert result.source_geometry.jaw_width >= result.donor_geometry.jaw_width - 0.1
    assert len(result.alternatives) == 2
    assert result.alternatives[0].player_id == result.player_id
    assert result.alternatives[0].score >= result.alternatives[1].score


def test_builder_prefers_complete_asset_set_when_geometry_is_equal(tmp_path: Path) -> None:
    photo = tmp_path / "photo.png"
    _write_png(photo, 0xFF9A7058)
    _asset_set(tmp_path, "100", 0xFF997058, complete=False)
    _asset_set(tmp_path, "200", 0xFF9E745C, complete=True)

    result = OneClickFaceBuilder().build(photo, tmp_path)

    assert result.player_id == "200"
    assert result.alternatives[0].complete


def test_rebuild_keeps_donor_corner_and_transfers_central_regions(tmp_path: Path) -> None:
    photo_path = tmp_path / "photo.png"
    donor_path = tmp_path / "donor.png"
    _write_png(photo_path, 0xFFC08060)
    _write_png(donor_path, 0xFF305070)
    builder = OneClickFaceBuilder()
    rebuilt = builder.rebuild_texture(builder._read(photo_path), builder._read(donor_path))

    assert rebuilt.pixelColor(10, 10) == QColor(0x30, 0x50, 0x70)
    assert rebuilt.pixelColor(512, 512) != QColor(0x30, 0x50, 0x70)


def test_builder_rejects_library_without_face_templates(tmp_path: Path) -> None:
    photo = tmp_path / "photo.png"
    _write_png(photo, 0xFF8C604A)
    (tmp_path / "100.skin").write_bytes(b"SKIN")

    with pytest.raises(ValueError, match="No complete FM26 face template"):
        OneClickFaceBuilder().build(photo, tmp_path)


def test_builder_rejects_missing_photo(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Image not found"):
        OneClickFaceBuilder().build(tmp_path / "missing.png", tmp_path)
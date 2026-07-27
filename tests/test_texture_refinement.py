from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtGui import QColor, QImage

from facestudio.match_engine_research.texture_refinement import (
    REFINEMENT_FORMAT, RefinementSettings, TextureRefinementService,
)


def _png(path: Path, colour: QColor) -> None:
    image = QImage(12, 12, QImage.Format.Format_ARGB32)
    image.fill(colour)
    assert image.save(str(path), "PNG")


def _manifest(tmp_path: Path) -> Path:
    donor = tmp_path / "donor.png"
    raw = tmp_path / "raw.png"
    _png(donor, QColor(100, 90, 80))
    _png(raw, QColor(100, 90, 80))
    image = QImage(str(raw))
    for y in range(3, 9):
        for x in range(3, 9):
            image.setPixelColor(x, y, QColor(170, 145, 130))
    image.setPixelColor(6, 6, QColor(100, 90, 80))
    assert image.save(str(raw), "PNG")
    path = tmp_path / "build.json"
    path.write_text(json.dumps({
        "format": "facestudio-texture-reconstruction-v1",
        "player_id": "55041632",
        "donor_texture": str(donor),
        "output_texture": str(raw),
    }), encoding="utf-8")
    return path


def test_refinement_repairs_gap_and_preserves_outside(tmp_path: Path) -> None:
    service = TextureRefinementService()
    result = service.refine(_manifest(tmp_path), RefinementSettings(4, 0.7, 0.4))
    assert result.player_id == "55041632"
    assert result.changed_pixels > 0
    assert result.gap_repairs == 1
    assert result.output.pixelColor(0, 0) == QColor(100, 90, 80, 255)
    assert result.output.pixelColor(5, 5) != QColor(100, 90, 80, 255)


def test_settings_are_clamped(tmp_path: Path) -> None:
    result = TextureRefinementService().refine(_manifest(tmp_path), RefinementSettings(99, -2, 4))
    assert result.settings.feather_radius == 20
    assert result.settings.colour_matching == 0.0
    assert result.settings.neighbour_blend == 1.0


def test_export_writes_v2_manifest(tmp_path: Path) -> None:
    service = TextureRefinementService()
    result = service.refine(_manifest(tmp_path))
    png, manifest = service.save(result, tmp_path / "refined")
    assert png.is_file()
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert payload["format"] == REFINEMENT_FORMAT
    assert payload["settings"]["feather_radius"] == 6
    assert payload["next_stage"] == "fm-texture-validation-and-controlled-game-test"


def test_rejects_wrong_manifest_format(tmp_path: Path) -> None:
    path = tmp_path / "wrong.json"
    path.write_text('{"format":"wrong"}', encoding="utf-8")
    try:
        TextureRefinementService().refine(path)
    except ValueError as exc:
        assert "facestudio-texture-reconstruction-v1" in str(exc)
    else:
        raise AssertionError("Expected invalid manifest to be rejected")

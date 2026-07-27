from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtGui import QColor, QImage
import pytest

from facestudio.match_engine_research.texture_validation import (
    BUILD_FORMAT,
    VALIDATION_FORMAT,
    TextureValidationService,
)


def _image(path: Path, changed: bool = False, size: int = 32) -> None:
    image = QImage(size, size, QImage.Format.Format_ARGB32)
    image.fill(QColor(125, 105, 92, 255))
    if changed:
        for y in range(8, 28):
            for x in range(8, 24):
                image.setPixelColor(x, y, QColor(145, 118, 100, 255))
    assert image.save(str(path), "PNG")


def _manifest(tmp_path: Path, *, changed: bool = True, format_name: str = "facestudio-texture-build-v2") -> Path:
    donor = tmp_path / "123.png"
    refined = tmp_path / "123-refined.png"
    _image(donor)
    _image(refined, changed=changed)
    manifest = tmp_path / "refined.json"
    manifest.write_text(json.dumps({
        "format": format_name,
        "player_id": "123",
        "donor_texture": str(donor),
        "output_texture": str(refined),
        "settings": {"feather_radius": 6, "colour_matching": 0.65, "neighbour_blend": 0.35},
        "changed_pixels": 320,
        "feathered_pixels": 64,
        "colour_adjusted_pixels": 320,
        "gap_repairs": 2,
    }), encoding="utf-8")
    return manifest


def test_validate_refined_texture(tmp_path: Path) -> None:
    result = TextureValidationService().validate(_manifest(tmp_path))
    assert result.player_id == "123"
    assert result.width == 32 and result.height == 32
    assert any(check.name == "Matching dimensions" and check.passed for check in result.checks)
    assert any(check.name == "Facial reconstruction present" and check.passed for check in result.checks)
    assert len(result.regions) == 9
    assert 0 <= result.quality_score <= 100
    assert not result.heatmap.isNull()


def test_rejects_wrong_manifest_format(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="facestudio-texture-build-v2"):
        TextureValidationService().validate(_manifest(tmp_path, format_name="wrong-format"))


def test_report_export(tmp_path: Path) -> None:
    service = TextureValidationService()
    result = service.validate(_manifest(tmp_path))
    json_path, html_path, heatmap_path = service.save_report(result, tmp_path / "report")
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["format"] == VALIDATION_FORMAT
    assert payload["player_id"] == "123"
    assert html_path.is_file()
    assert heatmap_path.is_file()


def test_reversible_package_contains_backup_and_manifest(tmp_path: Path) -> None:
    service = TextureValidationService()
    result = service.validate(_manifest(tmp_path))
    package = service.create_test_package(result, tmp_path / "packages")
    assert (package / "123.png").is_file()
    assert (package / "123.original.png").is_file()
    assert (package / "README.txt").is_file()
    payload = json.loads((package / "facestudio-build-v3.json").read_text(encoding="utf-8"))
    assert payload["format"] == BUILD_FORMAT
    assert payload["installation"] == "manual-and-reversible"
    assert payload["next_stage"] == "controlled-in-game-evaluation"


def test_power_of_two_check_is_transparent(tmp_path: Path) -> None:
    donor = tmp_path / "123.png"
    refined = tmp_path / "123-refined.png"
    _image(donor, size=30)
    _image(refined, changed=True, size=30)
    manifest = tmp_path / "refined.json"
    manifest.write_text(json.dumps({
        "format": "facestudio-texture-build-v2",
        "player_id": "123",
        "donor_texture": str(donor),
        "output_texture": str(refined),
    }), encoding="utf-8")
    result = TextureValidationService().validate(manifest)
    check = next(item for item in result.checks if item.name == "Power-of-two dimensions")
    assert check.passed is False

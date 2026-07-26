from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QColor, QImage

from facestudio.match_engine_research.auto_texture import AutoTextureAssistant


def _save(path: Path, width: int, height: int, colour: QColor) -> None:
    image = QImage(width, height, QImage.Format.Format_ARGB32)
    image.fill(colour)
    assert image.save(str(path), "PNG")


def test_auto_texture_preserves_template_dimensions(tmp_path: Path) -> None:
    photo = tmp_path / "photo.png"
    template = tmp_path / "template.png"
    _save(photo, 600, 800, QColor("#9a6a52"))
    _save(template, 1024, 1024, QColor("#76513f"))

    result = AutoTextureAssistant().generate("2000382120", photo, template)

    assert result.texture.width() == 1024
    assert result.texture.height() == 1024
    assert result.confidence >= 50
    assert result.settings.exclude_hair is True


def test_preview_head_is_transparent_square(tmp_path: Path) -> None:
    texture = QImage(1024, 1024, QImage.Format.Format_ARGB32)
    texture.fill(QColor("#8d6048"))

    preview = AutoTextureAssistant().preview_head(texture, yaw=35, size=360)

    assert preview.width() == 360
    assert preview.height() == 360
    assert preview.hasAlphaChannel()


def test_auto_texture_rejects_missing_photo(tmp_path: Path) -> None:
    template = tmp_path / "template.png"
    _save(template, 512, 512, QColor("#76513f"))

    try:
        AutoTextureAssistant().generate("123", tmp_path / "missing.png", template)
    except ValueError as exc:
        assert "not found" in str(exc).lower()
    else:
        raise AssertionError("Expected missing photo to be rejected")

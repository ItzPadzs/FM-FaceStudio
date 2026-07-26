from pathlib import Path

import pytest
from PySide6.QtGui import QImage

from facestudio.match_engine_research.texture_studio import TextureStudioService, TextureStudioSettings


def _save_image(path: Path, width: int, height: int) -> None:
    image = QImage(width, height, QImage.Format.Format_ARGB32)
    image.fill(0xFF9A725F)
    assert image.save(str(path), "PNG")


def test_texture_studio_preserves_template_dimensions(tmp_path: Path) -> None:
    photo = tmp_path / "photo.png"
    template = tmp_path / "template.png"
    _save_image(photo, 800, 1000)
    _save_image(template, 1024, 1024)

    result = TextureStudioService().render("2000382120", photo, template, TextureStudioSettings())

    assert result.width() == 1024
    assert result.height() == 1024


def test_texture_studio_exports_separate_png(tmp_path: Path) -> None:
    photo = tmp_path / "photo.png"
    template = tmp_path / "template.png"
    destination = tmp_path / "output"
    _save_image(photo, 500, 700)
    _save_image(template, 512, 512)
    before = template.read_bytes()

    result = TextureStudioService().save(
        "2000382120", photo, template, destination, TextureStudioSettings(brightness=10, saturation=90)
    )

    assert Path(result.destination).suffix == ".png"
    assert Path(result.destination).is_file()
    assert template.read_bytes() == before
    assert result.settings["brightness"] == 10


def test_texture_studio_rejects_invalid_id(tmp_path: Path) -> None:
    photo = tmp_path / "photo.png"
    template = tmp_path / "template.png"
    _save_image(photo, 100, 100)
    _save_image(template, 100, 100)

    with pytest.raises(ValueError, match="digits only"):
        TextureStudioService().render("abc", photo, template, TextureStudioSettings())


def test_texture_studio_validates_controls(tmp_path: Path) -> None:
    photo = tmp_path / "photo.png"
    template = tmp_path / "template.png"
    _save_image(photo, 100, 100)
    _save_image(template, 100, 100)

    with pytest.raises(ValueError, match="at least 10"):
        TextureStudioService().render(
            "1", photo, template, TextureStudioSettings(target_width=5)
        )

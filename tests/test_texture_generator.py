from pathlib import Path

from PySide6.QtGui import QColor, QImage

from facestudio.texture_generator import HeadTextureGenerator, UV_TEXTURE_FORMAT


def _write_image(path: Path, width: int, height: int, colour: str) -> None:
    image = QImage(width, height, QImage.Format.Format_ARGB32)
    image.fill(QColor(colour))
    assert image.save(str(path), "PNG")


def test_generates_square_png_and_manifest(tmp_path: Path) -> None:
    photo = tmp_path / "portrait.png"
    _write_image(photo, 800, 1000, "#aa785f")

    result = HeadTextureGenerator().build(photo, tmp_path / "out", size=1024)

    assert result.texture.is_file()
    assert result.manifest.is_file()
    generated = QImage(str(result.texture))
    assert generated.size().width() == 1024
    assert generated.size().height() == 1024
    assert UV_TEXTURE_FORMAT in result.manifest.read_text(encoding="utf-8")


def test_accepts_existing_texture_template(tmp_path: Path) -> None:
    photo = tmp_path / "portrait.png"
    template = tmp_path / "template.png"
    _write_image(photo, 640, 900, "#a06e5a")
    _write_image(template, 1024, 1024, "#5a463c")

    result = HeadTextureGenerator().build(photo, tmp_path / "out", template=template)

    assert result.texture.suffix == ".png"
    assert not QImage(str(result.texture)).isNull()


def test_generator_has_no_optional_runtime_dependency() -> None:
    assert HeadTextureGenerator.available() is True

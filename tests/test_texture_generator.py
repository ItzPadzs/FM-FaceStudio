from pathlib import Path

from PIL import Image

from facestudio.texture_generator import HeadTextureGenerator, UV_TEXTURE_FORMAT


def test_generates_square_png_and_manifest(tmp_path: Path) -> None:
    photo = tmp_path / "portrait.png"
    Image.new("RGB", (800, 1000), (170, 120, 95)).save(photo)

    result = HeadTextureGenerator().build(photo, tmp_path / "out", size=1024)

    assert result.texture.is_file()
    assert result.manifest.is_file()
    assert Image.open(result.texture).size == (1024, 1024)
    assert UV_TEXTURE_FORMAT in result.manifest.read_text(encoding="utf-8")


def test_accepts_existing_texture_template(tmp_path: Path) -> None:
    photo = tmp_path / "portrait.png"
    template = tmp_path / "template.png"
    Image.new("RGB", (640, 900), (160, 110, 90)).save(photo)
    Image.new("RGB", (1024, 1024), (90, 70, 60)).save(template)

    result = HeadTextureGenerator().build(photo, tmp_path / "out", template=template)

    assert result.texture.suffix == ".png"
    assert Image.open(result.texture).mode == "RGB"

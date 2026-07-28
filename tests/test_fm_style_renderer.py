from __future__ import annotations

from PySide6.QtGui import QColor, QImage

from facestudio.ai.fm_style_renderer import FMStyleRendererEngine


def _sample_image(size: int = 48) -> QImage:
    image = QImage(size, size, QImage.Format.Format_ARGB32)
    for y in range(size):
        for x in range(size):
            image.setPixelColor(x, y, QColor(80 + x * 2, 60 + y * 2, 50 + (x + y), 255))
    return image


def test_style_renderer_is_available() -> None:
    engine = FMStyleRendererEngine()
    assert engine.available
    assert engine.name == "fm-style-renderer-v1"


def test_tone_map_preserves_dimensions_and_compresses_range() -> None:
    engine = FMStyleRendererEngine()
    source = _sample_image()
    result = engine._diffuse_tone_map(source)
    assert result.size() == source.size()
    assert result.pixelColor(47, 47).red() < source.pixelColor(47, 47).red()


def test_diffuse_grain_is_deterministic() -> None:
    engine = FMStyleRendererEngine()
    source = _sample_image()
    first = engine._add_diffuse_grain(source)
    second = engine._add_diffuse_grain(source)
    assert first == second
    assert first != source


def test_frequency_balance_preserves_alpha_and_size() -> None:
    engine = FMStyleRendererEngine()
    source = _sample_image()
    result = engine._frequency_balance(source)
    assert result.size() == source.size()
    assert result.pixelColor(20, 20).alpha() == 255

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtGui import QColor, QImage


@dataclass(frozen=True)
class SkinCandidate:
    image: QImage
    mask: QImage


def _skin_likelihood(colour: QColor) -> int:
    """Return a conservative 0-255 skin likelihood from RGB relationships.

    This is intentionally deterministic and dependency-free. It is a bootstrap mask,
    not a demographic classifier; later versions can replace it with a learned parser.
    """
    r, g, b = colour.red(), colour.green(), colour.blue()
    maximum, minimum = max(r, g, b), min(r, g, b)
    classic = r > 40 and g > 20 and b > 10 and maximum - minimum > 10 and r >= g and r >= b
    low_light = r > 20 and g > 15 and b > 10 and abs(r - g) > 3 and r >= b
    if not (classic or low_light):
        return 0
    chroma = min(80, maximum - minimum)
    warmth = max(0, min(80, r - b + 30))
    return min(255, 80 + chroma + warmth)


def extract_skin_candidate(aligned_portrait: QImage) -> SkinCandidate:
    """Extract a same-size candidate and grayscale confidence mask.

    The input must already be aligned to the donor UV. No crop, scale or warp occurs.
    """
    if aligned_portrait.isNull():
        raise ValueError("aligned portrait is empty")
    source = aligned_portrait.convertToFormat(QImage.Format.Format_RGB32)
    mask = QImage(source.size(), QImage.Format.Format_Grayscale8)
    mask.fill(0)
    for y in range(source.height()):
        for x in range(source.width()):
            value = _skin_likelihood(source.pixelColor(x, y))
            mask.setPixelColor(x, y, QColor(value, value, value))
    return SkinCandidate(source, mask)

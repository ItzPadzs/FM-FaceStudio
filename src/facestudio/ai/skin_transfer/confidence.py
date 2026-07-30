from __future__ import annotations

from PySide6.QtGui import QColor, QImage


def combine_confidence(candidate_mask: QImage, protection_mask: QImage) -> QImage:
    """Combine candidate confidence with donor-protection regions.

    White protection pixels force confidence to zero, ensuring sensitive UV regions are
    copied from the donor unchanged.
    """
    if candidate_mask.size() != protection_mask.size():
        raise ValueError("candidate and protection masks must have the same dimensions")
    output = QImage(candidate_mask.size(), QImage.Format.Format_Grayscale8)
    for y in range(output.height()):
        for x in range(output.width()):
            candidate = candidate_mask.pixelColor(x, y).red()
            protected = protection_mask.pixelColor(x, y).red()
            value = round(candidate * (255 - protected) / 255)
            output.setPixelColor(x, y, QColor(value, value, value))
    return output

from __future__ import annotations

from PySide6.QtGui import QColor, QImage


def composite(source: QImage, donor: QImage, confidence: QImage) -> QImage:
    """Blend source surface colour over donor while preserving donor geometry."""
    if source.size() != donor.size() or source.size() != confidence.size():
        raise ValueError("source, donor and confidence images must share dimensions")
    source = source.convertToFormat(QImage.Format.Format_RGB32)
    donor = donor.convertToFormat(QImage.Format.Format_RGB32)
    output = QImage(source.size(), QImage.Format.Format_RGB32)
    for y in range(output.height()):
        for x in range(output.width()):
            alpha = confidence.pixelColor(x, y).red() / 255.0
            src = source.pixelColor(x, y)
            dst = donor.pixelColor(x, y)
            output.setPixelColor(
                x,
                y,
                QColor(
                    round(dst.red() * (1.0 - alpha) + src.red() * alpha),
                    round(dst.green() * (1.0 - alpha) + src.green() * alpha),
                    round(dst.blue() * (1.0 - alpha) + src.blue() * alpha),
                ),
            )
    return output

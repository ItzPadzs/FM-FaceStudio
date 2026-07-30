from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QRectF
from PySide6.QtGui import QColor, QImage, QPainter


@dataclass(frozen=True)
class ProtectedRegions:
    eyes: tuple[QRectF, QRectF]
    nostrils: QRectF
    mouth: QRectF
    ears: tuple[QRectF, QRectF]


def default_fm_regions() -> ProtectedRegions:
    """Normalised conservative regions for a 1024-style FM face atlas."""
    return ProtectedRegions(
        eyes=(QRectF(0.31, 0.33, 0.16, 0.10), QRectF(0.53, 0.33, 0.16, 0.10)),
        nostrils=QRectF(0.43, 0.48, 0.14, 0.09),
        mouth=QRectF(0.39, 0.57, 0.22, 0.13),
        ears=(QRectF(0.08, 0.34, 0.14, 0.27), QRectF(0.78, 0.34, 0.14, 0.27)),
    )


def build_protection_mask(size, regions: ProtectedRegions | None = None) -> QImage:
    """Return grayscale mask: white means preserve donor pixels exactly."""
    regions = regions or default_fm_regions()
    mask = QImage(size, QImage.Format.Format_Grayscale8)
    mask.fill(0)
    painter = QPainter(mask)
    painter.setPen(QColor(255, 255, 255))
    painter.setBrush(QColor(255, 255, 255))
    for rect in (*regions.eyes, regions.nostrils, regions.mouth, *regions.ears):
        painter.drawEllipse(
            QRectF(rect.x() * size.width(), rect.y() * size.height(), rect.width() * size.width(), rect.height() * size.height())
        )
    painter.end()
    return mask

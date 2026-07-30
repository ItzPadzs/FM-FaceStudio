from __future__ import annotations

from dataclasses import dataclass
from statistics import median

from PySide6.QtGui import QColor, QImage


@dataclass(frozen=True)
class ColourShift:
    red: float
    green: float
    blue: float


def _masked_channel_medians(image: QImage, mask: QImage) -> tuple[float, float, float]:
    samples_r: list[int] = []
    samples_g: list[int] = []
    samples_b: list[int] = []
    step = max(1, min(image.width(), image.height()) // 256)
    for y in range(0, image.height(), step):
        for x in range(0, image.width(), step):
            if mask.pixelColor(x, y).red() < 96:
                continue
            colour = image.pixelColor(x, y)
            samples_r.append(colour.red())
            samples_g.append(colour.green())
            samples_b.append(colour.blue())
    if not samples_r:
        return 0.0, 0.0, 0.0
    return float(median(samples_r)), float(median(samples_g)), float(median(samples_b))


def compute_colour_shift(source: QImage, donor: QImage, mask: QImage) -> ColourShift:
    """Compute a robust median RGB shift without altering geometry.

    A future OpenCV-backed implementation can perform true CIE Lab matching behind the
    same interface. The median-based bootstrap is stable and has no optional dependency.
    """
    source_median = _masked_channel_medians(source, mask)
    donor_median = _masked_channel_medians(donor, mask)
    return ColourShift(*(donor_median[i] - source_median[i] for i in range(3)))


def apply_colour_shift(image: QImage, shift: ColourShift, strength: float = 1.0) -> QImage:
    strength = max(0.0, min(1.0, strength))
    source = image.convertToFormat(QImage.Format.Format_RGB32)
    output = QImage(source.size(), QImage.Format.Format_RGB32)
    for y in range(source.height()):
        for x in range(source.width()):
            c = source.pixelColor(x, y)
            output.setPixelColor(
                x,
                y,
                QColor(
                    max(0, min(255, round(c.red() + shift.red * strength))),
                    max(0, min(255, round(c.green() + shift.green * strength))),
                    max(0, min(255, round(c.blue() + shift.blue * strength))),
                ),
            )
    return output

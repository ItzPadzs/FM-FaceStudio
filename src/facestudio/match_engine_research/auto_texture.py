from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QPointF, QRect, Qt
from PySide6.QtGui import QColor, QImage, QImageReader, QPainter, QPainterPath, QRadialGradient

from facestudio.match_engine_research.texture_studio import TextureStudioService, TextureStudioSettings


@dataclass(frozen=True)
class AutoTextureResult:
    texture: QImage
    settings: TextureStudioSettings
    confidence: int
    notes: tuple[str, ...]


class AutoTextureAssistant:
    """Local deterministic assistant for producing a first-pass UV draft.

    This does not call a hosted AI service or reconstruct unseen geometry. It
    analyses image proportions and applies a conservative preset derived from
    the observed FM26 face-texture layout, leaving the user free to refine it.
    """

    def __init__(self) -> None:
        self.renderer = TextureStudioService()

    def generate(self, player_id: str, photo_path: Path, template_path: Path) -> AutoTextureResult:
        photo = self._read(photo_path)
        template = self._read(template_path)
        if photo.isNull() or template.isNull():
            raise ValueError("The photo or template could not be decoded.")

        portrait_ratio = photo.height() / max(1, photo.width())
        crop_size = 60 if portrait_ratio >= 1.05 else 72
        crop_y = 40 if portrait_ratio >= 1.05 else 46
        settings = TextureStudioSettings(
            crop_x=50,
            crop_y=crop_y,
            crop_size=crop_size,
            target_x=29,
            target_y=18,
            target_width=42,
            target_height=57,
            opacity=94,
            feather=22,
            brightness=0,
            saturation=92,
            exclude_hair=True,
        )
        texture = self.renderer.render(player_id, photo_path, template_path, settings)
        confidence = 70 if portrait_ratio >= 0.9 else 55
        notes = (
            "Automatic first-pass alignment applied.",
            "Hair is faded because FM26 can use separate hair assets.",
            "Ears, scalp and unseen side-profile detail still come from the template.",
        )
        return AutoTextureResult(texture=texture, settings=settings, confidence=confidence, notes=notes)

    def preview_head(self, texture: QImage, yaw: int = 0, size: int = 420) -> QImage:
        yaw = max(-60, min(60, yaw))
        canvas = QImage(size, size, QImage.Format.Format_ARGB32)
        canvas.fill(Qt.GlobalColor.transparent)
        painter = QPainter(canvas)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        head = QRect(round(size * 0.19), round(size * 0.08), round(size * 0.62), round(size * 0.82))
        path = QPainterPath()
        path.addEllipse(head)
        painter.setClipPath(path)

        face_crop = texture.copy(
            round(texture.width() * 0.27), round(texture.height() * 0.12),
            round(texture.width() * 0.46), round(texture.height() * 0.72),
        )
        horizontal_shift = round(yaw / 60 * head.width() * 0.18)
        projected = QRect(head.x() + horizontal_shift, head.y(), head.width(), head.height())
        painter.drawImage(projected, face_crop)

        gradient = QRadialGradient(QPointF(head.center().x() - yaw * 1.2, head.center().y() - head.height() * 0.18), head.width() * 0.72)
        gradient.setColorAt(0.0, QColor(255, 255, 255, 35))
        gradient.setColorAt(0.68, QColor(0, 0, 0, 15))
        gradient.setColorAt(1.0, QColor(0, 0, 0, 120))
        painter.fillPath(path, gradient)
        painter.setClipping(False)
        painter.setPen(QColor(255, 255, 255, 55))
        painter.drawEllipse(head)
        painter.end()
        return canvas

    @staticmethod
    def _read(path: Path) -> QImage:
        if not path.is_file():
            raise ValueError(f"Image not found: {path}")
        reader = QImageReader(str(path))
        reader.setAutoTransform(True)
        return reader.read()

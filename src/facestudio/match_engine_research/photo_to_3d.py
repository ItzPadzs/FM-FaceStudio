from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QPointF, QRect, Qt
from PySide6.QtGui import QColor, QImage, QImageReader, QLinearGradient, QPainter, QPainterPath, QRadialGradient

from facestudio.match_engine_research.auto_texture import AutoTextureAssistant, AutoTextureResult


@dataclass(frozen=True)
class Photo3DResult:
    preview: QImage
    yaw: int
    depth_strength: int
    source_width: int
    source_height: int


class PhotoTo3DService:
    """Create a local single-photo 3D-style likeness and FM26 texture fallback.

    A single photograph cannot reveal true hidden geometry. The preview therefore
    uses a documented depth-and-wrap approximation. When a matching FM26 template
    is supplied, texture transfer uses the existing local automatic UV assistant.
    """

    def create_preview(self, photo_path: Path, yaw: int = 0, depth_strength: int = 55, size: int = 520) -> Photo3DResult:
        source = self._read(photo_path)
        if source.isNull():
            raise ValueError("The selected photograph could not be decoded.")
        yaw = max(-65, min(65, yaw))
        depth_strength = max(0, min(100, depth_strength))
        canvas = QImage(size, size, QImage.Format.Format_ARGB32)
        canvas.fill(Qt.GlobalColor.transparent)

        face = self._portrait_crop(source)
        painter = QPainter(canvas)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        head = QRect(round(size * 0.18), round(size * 0.05), round(size * 0.64), round(size * 0.88))
        silhouette = QPainterPath()
        silhouette.addRoundedRect(head, head.width() * 0.46, head.height() * 0.34)
        painter.setClipPath(silhouette)

        squeeze = 1.0 - abs(yaw) / 65 * 0.30
        projected_width = max(1, round(head.width() * squeeze))
        shift = round(yaw / 65 * head.width() * 0.18)
        projected = QRect(head.center().x() - projected_width // 2 + shift, head.y(), projected_width, head.height())
        painter.drawImage(projected, face)

        side_amount = int(35 + depth_strength * 0.9)
        side = QLinearGradient(head.left(), 0, head.right(), 0)
        if yaw >= 0:
            side.setColorAt(0.0, QColor(0, 0, 0, side_amount))
            side.setColorAt(0.55, QColor(255, 255, 255, 8))
            side.setColorAt(1.0, QColor(0, 0, 0, 12))
        else:
            side.setColorAt(0.0, QColor(0, 0, 0, 12))
            side.setColorAt(0.45, QColor(255, 255, 255, 8))
            side.setColorAt(1.0, QColor(0, 0, 0, side_amount))
        painter.fillPath(silhouette, side)

        centre = QPointF(head.center().x() - yaw * 0.75, head.center().y() - head.height() * 0.16)
        depth = QRadialGradient(centre, head.width() * 0.82)
        depth.setColorAt(0.0, QColor(255, 255, 255, round(depth_strength * 0.30)))
        depth.setColorAt(0.62, QColor(0, 0, 0, 0))
        depth.setColorAt(1.0, QColor(0, 0, 0, round(45 + depth_strength * 0.75)))
        painter.fillPath(silhouette, depth)
        painter.setClipping(False)
        painter.setPen(QColor(255, 255, 255, 42))
        painter.drawPath(silhouette)
        painter.end()

        return Photo3DResult(canvas, yaw, depth_strength, source.width(), source.height())

    def transfer_to_template(self, player_id: str, photo_path: Path, template_path: Path) -> AutoTextureResult:
        return AutoTextureAssistant().generate(player_id, photo_path, template_path)

    @staticmethod
    def _portrait_crop(image: QImage) -> QImage:
        target_ratio = 0.78
        width, height = image.width(), image.height()
        if width / max(1, height) > target_ratio:
            crop_width = round(height * target_ratio)
            x = max(0, (width - crop_width) // 2)
            return image.copy(x, 0, crop_width, height)
        crop_height = round(width / target_ratio)
        y = max(0, min(height - crop_height, (height - crop_height) // 3))
        return image.copy(0, y, width, crop_height)

    @staticmethod
    def _read(path: Path) -> QImage:
        if not path.is_file():
            raise ValueError(f"Image not found: {path}")
        reader = QImageReader(str(path))
        reader.setAutoTransform(True)
        return reader.read()

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QImage, QImageReader, QPainter, QPainterPath


@dataclass(frozen=True)
class TextureBuildResult:
    destination: str
    width: int
    height: int
    player_id: str


class PhotoTextureBuilder:
    """Create a conservative photo-on-template UV texture prototype.

    The builder preserves the selected FM26 texture as a template and blends a
    centre-cropped user photo into the observed central face region. It does
    not claim automatic landmark alignment, full UV reconstruction or a final
    match-engine-ready likeness.
    """

    def build(
        self,
        player_id: str,
        photo_path: Path,
        template_path: Path,
        destination: Path,
        opacity: float = 0.92,
    ) -> TextureBuildResult:
        player_id = player_id.strip()
        if not player_id.isdigit():
            raise ValueError("Football Manager unique ID must contain digits only.")
        if not photo_path.is_file():
            raise ValueError("Choose a source photograph that exists.")
        if not template_path.is_file():
            raise ValueError("The selected player does not have a usable face PNG template.")
        if not 0.05 <= opacity <= 1.0:
            raise ValueError("Opacity must be between 0.05 and 1.0.")

        photo = self._read_image(photo_path)
        template = self._read_image(template_path).convertToFormat(QImage.Format.Format_ARGB32)
        if photo.isNull() or template.isNull():
            raise ValueError("The photograph or template could not be decoded as an image.")

        crop = self._centre_square(photo)
        target = QRect(
            round(template.width() * 0.285),
            round(template.height() * 0.175),
            round(template.width() * 0.43),
            round(template.height() * 0.58),
        )
        fitted = crop.scaled(
            target.size(),
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        result = template.copy()
        painter = QPainter(result)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        face_mask = QPainterPath()
        face_mask.addEllipse(target.adjusted(0, 0, -1, -1))
        painter.setClipPath(face_mask)
        painter.setOpacity(opacity)
        painter.drawImage(target, fitted)
        painter.end()

        destination = destination.expanduser()
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.suffix.lower() != ".png":
            destination = destination.with_suffix(".png")
        if not result.save(str(destination), "PNG"):
            raise OSError(f"Could not save texture to {destination}")
        return TextureBuildResult(
            destination=str(destination),
            width=result.width(),
            height=result.height(),
            player_id=player_id,
        )

    @staticmethod
    def _read_image(path: Path) -> QImage:
        reader = QImageReader(str(path))
        reader.setAutoTransform(True)
        return reader.read()

    @staticmethod
    def _centre_square(image: QImage) -> QImage:
        side = min(image.width(), image.height())
        x = max(0, (image.width() - side) // 2)
        # Bias slightly upward because ordinary portraits include more space
        # below the chin than above the forehead.
        y = max(0, min(image.height() - side, (image.height() - side) // 3))
        return image.copy(x, y, side, side)

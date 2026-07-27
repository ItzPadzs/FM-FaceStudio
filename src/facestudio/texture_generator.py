from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from PySide6.QtCore import QPointF, QRect, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QImageReader, QPainter, QPainterPath, QPolygonF

UV_TEXTURE_FORMAT = "facestudio-head-texture-v3"


@dataclass(frozen=True)
class TextureBuildResult:
    texture: Path
    manifest: Path
    size: int


class HeadTextureGenerator:
    """Create an FM/BepInEx head texture from a frontal portrait and working template.

    The working FM texture remains responsible for the UV layout, scalp, ears, sides,
    neck and expression openings. Only the portrait's inner facial identity is fitted
    into the template face region. This avoids pasting the source photograph, hair and
    background as one rectangular image.
    """

    @staticmethod
    def available() -> bool:
        return True

    @staticmethod
    def dependency_message() -> str:
        return "The built-in Qt texture generator is available."

    def build(
        self,
        photo: Path,
        output_directory: Path,
        *,
        template: Path | None = None,
        size: int = 1024,
        face_scale: float = 1.0,
        face_y: float = 0.0,
        smoothing: float = 0.35,
    ) -> TextureBuildResult:
        photo = Path(photo).expanduser().resolve()
        output_directory = Path(output_directory).expanduser().resolve()
        if not photo.is_file():
            raise ValueError(f"Photograph not found: {photo}")
        if size not in (512, 1024, 2048):
            raise ValueError("Texture size must be 512, 1024 or 2048")
        if template is None:
            raise ValueError(
                "Choose one known-working FM/BepInEx head texture first. "
                "The template supplies the required UV layout, ears, scalp, neck and openings."
            )

        template_path = Path(template).expanduser().resolve()
        if not template_path.is_file():
            raise ValueError(f"Template not found: {template_path}")

        portrait = self._read_image(photo)
        portrait = self._portrait_face_crop(portrait, face_scale, face_y)
        base = self._read_image(template_path).scaled(
            size,
            size,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        canvas = self._fit_identity_to_template(base, portrait, size, smoothing)

        output_directory.mkdir(parents=True, exist_ok=True)
        texture = output_directory / f"{photo.stem}-head-texture.png"
        if not canvas.save(str(texture), "PNG"):
            raise OSError(f"Could not save generated texture: {texture}")

        manifest = output_directory / f"{photo.stem}-head-texture.json"
        manifest.write_text(
            json.dumps(
                {
                    "format": UV_TEXTURE_FORMAT,
                    "generator": "qt-template-identity-fit",
                    "source_photo": str(photo),
                    "template": str(template_path),
                    "texture": str(texture),
                    "size": size,
                    "face_scale": face_scale,
                    "face_y": face_y,
                    "smoothing": smoothing,
                    "preserved_template_regions": [
                        "hair_and_scalp",
                        "ears",
                        "outer_cheeks",
                        "neck",
                        "eye_openings",
                        "mouth_opening",
                        "uv_boundaries",
                    ],
                    "identity_region": {
                        "left": 0.215,
                        "top": 0.155,
                        "right": 0.785,
                        "bottom": 0.805,
                    },
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return TextureBuildResult(texture=texture, manifest=manifest, size=size)

    @staticmethod
    def _read_image(path: Path) -> QImage:
        reader = QImageReader(str(path))
        reader.setAutoTransform(True)
        image = reader.read()
        if image.isNull():
            detail = reader.errorString() or "unsupported or damaged image"
            raise ValueError(f"Could not open image {path}: {detail}")
        return image.convertToFormat(QImage.Format.Format_ARGB32)

    @staticmethod
    def _portrait_face_crop(image: QImage, scale: float, y_offset: float) -> QImage:
        """Crop the likely inner face rather than copying the complete photograph."""
        width, height = image.width(), image.height()
        scale = max(0.72, min(1.45, float(scale)))

        crop_width = min(width, max(1, int(width * 0.72 / scale)))
        crop_height = min(height, max(1, int(height * 0.82 / scale)))
        centre_x = width // 2
        centre_y = int(height * (0.49 + max(-0.20, min(0.20, float(y_offset)))))
        left = max(0, min(width - crop_width, centre_x - crop_width // 2))
        top = max(0, min(height - crop_height, centre_y - crop_height // 2))
        return image.copy(QRect(left, top, crop_width, crop_height))

    @staticmethod
    def _fit_identity_to_template(
        template: QImage,
        portrait: QImage,
        size: int,
        smoothing: float,
    ) -> QImage:
        out = template.copy()
        painter = QPainter(out)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # Target matches the inner facial identity region found in the supplied working
        # head textures. Hair, ears, extreme cheeks and neck remain from the template.
        target = QRectF(size * 0.215, size * 0.155, size * 0.57, size * 0.65)

        mask = QPainterPath()
        mask.addEllipse(QRectF(size * 0.215, size * 0.145, size * 0.57, size * 0.625))
        jaw = QPolygonF(
            [
                QPointF(size * 0.255, size * 0.49),
                QPointF(size * 0.30, size * 0.705),
                QPointF(size * 0.405, size * 0.805),
                QPointF(size * 0.50, size * 0.835),
                QPointF(size * 0.595, size * 0.805),
                QPointF(size * 0.70, size * 0.705),
                QPointF(size * 0.745, size * 0.49),
            ]
        )
        jaw_path = QPainterPath()
        jaw_path.addPolygon(jaw)
        mask = mask.united(jaw_path)

        painter.setClipPath(mask)
        painter.setOpacity(0.90)
        painter.drawImage(target, portrait)
        painter.end()

        # A soft second pass reduces the hard edge without blurring the complete atlas.
        amount = max(0.0, min(1.0, float(smoothing)))
        if amount > 0:
            softened = out.scaled(
                max(1, size // 10),
                max(1, size // 10),
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            ).scaled(
                size,
                size,
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            blend = QPainter(out)
            blend.setClipPath(mask)
            blend.setOpacity(amount * 0.08)
            blend.drawImage(QPointF(0, 0), softened)
            blend.end()

        return out

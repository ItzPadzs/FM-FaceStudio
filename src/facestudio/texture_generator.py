from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from PySide6.QtCore import QPointF, QRect, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QImageReader, QPainter, QPainterPath

UV_TEXTURE_FORMAT = "facestudio-head-texture-v2"


@dataclass(frozen=True)
class TextureBuildResult:
    texture: Path
    manifest: Path
    size: int


class HeadTextureGenerator:
    """Create a square FM/BepInEx-style head texture using PySide6 only.

    The generator deliberately uses the same Qt installation as the interface, so a
    separate Pillow installation is no longer required. A working FM head texture can
    be supplied as the base; the portrait is then projected into its central face area
    while the template preserves the scalp, ears, neck and outer UV coverage.
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

        source = self._read_image(photo)
        source = self._square_face_crop(source, face_scale, face_y)
        source = source.scaled(
            size,
            size,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        template_path: Path | None = None
        if template is not None:
            template_path = Path(template).expanduser().resolve()
            if not template_path.is_file():
                raise ValueError(f"Template not found: {template_path}")
            canvas = self._read_image(template_path).scaled(
                size,
                size,
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        else:
            canvas = self._neutral_canvas(source, size)

        canvas = self._compose_face(canvas, source, size)
        if template_path is None:
            canvas = self._extend_sides(canvas, size)
            canvas = self._extend_neck(canvas, size)
        canvas = self._soften(canvas, smoothing)

        output_directory.mkdir(parents=True, exist_ok=True)
        texture = output_directory / f"{photo.stem}-head-texture.png"
        if not canvas.save(str(texture), "PNG"):
            raise OSError(f"Could not save generated texture: {texture}")

        manifest = output_directory / f"{photo.stem}-head-texture.json"
        manifest.write_text(
            json.dumps(
                {
                    "format": UV_TEXTURE_FORMAT,
                    "generator": "qt-native",
                    "source_photo": str(photo),
                    "template": str(template_path) if template_path else None,
                    "texture": str(texture),
                    "size": size,
                    "face_scale": face_scale,
                    "face_y": face_y,
                    "smoothing": smoothing,
                    "target_layout": {
                        "left_ear": [0.13, 0.48],
                        "right_ear": [0.87, 0.48],
                        "left_eye": [0.39, 0.39],
                        "right_eye": [0.61, 0.39],
                        "nose": [0.50, 0.51],
                        "mouth": [0.50, 0.62],
                        "chin": [0.50, 0.75],
                        "neck_start": 0.73,
                    },
                    "note": (
                        "Using a known working head texture as the base gives the most "
                        "reliable scalp, ear, neck and UV-boundary placement."
                    ),
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
    def _square_face_crop(image: QImage, scale: float, y_offset: float) -> QImage:
        width, height = image.width(), image.height()
        scale = max(0.65, min(1.60, float(scale)))
        side = max(1, min(width, height, int(min(width, height) / scale)))
        centre_x = width // 2
        centre_y = int(height * (0.50 + max(-0.25, min(0.25, float(y_offset)))))
        left = max(0, min(width - side, centre_x - side // 2))
        top = max(0, min(height - side, centre_y - side // 2))
        return image.copy(QRect(left, top, side, side))

    @staticmethod
    def _neutral_canvas(source: QImage, size: int) -> QImage:
        sample = source.scaled(
            1,
            1,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        colour = QColor(sample.pixel(0, 0))
        canvas = QImage(size, size, QImage.Format.Format_ARGB32)
        canvas.fill(colour)
        return canvas

    @staticmethod
    def _compose_face(canvas: QImage, source: QImage, size: int) -> QImage:
        out = canvas.copy()
        painter = QPainter(out)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # The central portrait occupies the same broad region visible in the supplied
        # working textures. The curved clip preserves the base texture around the ears,
        # scalp and extreme sides instead of replacing the whole atlas with a square.
        target = QRectF(size * 0.145, size * 0.075, size * 0.71, size * 0.84)
        clip = QPainterPath()
        clip.addEllipse(QRectF(size * 0.14, size * 0.07, size * 0.72, size * 0.84))
        lower = QPainterPath()
        lower.addRoundedRect(
            QRectF(size * 0.19, size * 0.48, size * 0.62, size * 0.43),
            size * 0.08,
            size * 0.08,
        )
        clip = clip.united(lower)
        painter.setClipPath(clip)
        painter.setOpacity(0.96)
        painter.drawImage(target, source)
        painter.end()
        return out

    @staticmethod
    def _extend_sides(image: QImage, size: int) -> QImage:
        out = image.copy()
        painter = QPainter(out)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        left_source = QRect(int(size * 0.15), int(size * 0.18), int(size * 0.17), int(size * 0.70))
        right_source = QRect(int(size * 0.68), int(size * 0.18), int(size * 0.17), int(size * 0.70))
        painter.drawImage(QRectF(0, size * 0.18, size * 0.23, size * 0.72), image, QRectF(left_source))
        painter.drawImage(QRectF(size * 0.77, size * 0.18, size * 0.23, size * 0.72), image, QRectF(right_source))
        painter.end()
        return out

    @staticmethod
    def _extend_neck(image: QImage, size: int) -> QImage:
        out = image.copy()
        painter = QPainter(out)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        source = QRectF(size * 0.20, size * 0.69, size * 0.60, size * 0.18)
        target = QRectF(0, size * 0.70, size, size * 0.30)
        painter.drawImage(target, image, source)
        painter.end()
        return out

    @staticmethod
    def _soften(image: QImage, amount: float) -> QImage:
        amount = max(0.0, min(1.0, float(amount)))
        if amount <= 0.0:
            return image
        factor = max(8, int(24 - amount * 14))
        small = image.scaled(
            max(1, image.width() // factor),
            max(1, image.height() // factor),
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        blurred = small.scaled(
            image.width(),
            image.height(),
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        out = image.copy()
        painter = QPainter(out)
        painter.setOpacity(amount * 0.12)
        painter.drawImage(QPointF(0, 0), blurred)
        painter.end()
        return out

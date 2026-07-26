from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QImage, QImageReader, QPainter, QPainterPath


@dataclass(frozen=True)
class TextureStudioSettings:
    crop_x: int = 50
    crop_y: int = 38
    crop_size: int = 62
    target_x: int = 29
    target_y: int = 18
    target_width: int = 42
    target_height: int = 57
    opacity: int = 92
    feather: int = 12
    brightness: int = 0
    saturation: int = 100
    exclude_hair: bool = True


@dataclass(frozen=True)
class TextureStudioResult:
    destination: str
    player_id: str
    width: int
    height: int
    settings: dict[str, object]


class TextureStudioService:
    """Local, non-destructive photo-to-observed-UV authoring controls.

    This first Texture Studio release deliberately uses a user-selected existing
    FM26 face PNG as the observed layout template. It provides controlled crop,
    placement, feathering and colour adjustment, but does not claim automatic
    landmark detection, full 3D reconstruction or guaranteed game acceptance.
    """

    def render(
        self,
        player_id: str,
        photo_path: Path,
        template_path: Path,
        settings: TextureStudioSettings,
    ) -> QImage:
        player_id = player_id.strip()
        if not player_id.isdigit():
            raise ValueError("Football Manager unique ID must contain digits only.")
        if not photo_path.is_file():
            raise ValueError("Choose a source photograph that exists.")
        if not template_path.is_file():
            raise ValueError("Choose a valid FM26 face PNG template.")
        self._validate(settings)

        photo = self._read(photo_path).convertToFormat(QImage.Format.Format_ARGB32)
        template = self._read(template_path).convertToFormat(QImage.Format.Format_ARGB32)
        if photo.isNull() or template.isNull():
            raise ValueError("The photograph or template could not be decoded.")

        crop = self._crop(photo, settings)
        crop = self._adjust(crop, settings)
        target = QRect(
            round(template.width() * settings.target_x / 100),
            round(template.height() * settings.target_y / 100),
            max(1, round(template.width() * settings.target_width / 100)),
            max(1, round(template.height() * settings.target_height / 100)),
        )
        fitted = crop.scaled(target.size(), Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)

        result = template.copy()
        painter = QPainter(result)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        mask = QPainterPath()
        inset = max(0, round(min(target.width(), target.height()) * settings.feather / 200))
        mask.addEllipse(target.adjusted(inset, inset, -inset, -inset))
        painter.setClipPath(mask)
        painter.setOpacity(settings.opacity / 100)
        painter.drawImage(target, fitted)
        painter.end()
        return result

    def save(
        self,
        player_id: str,
        photo_path: Path,
        template_path: Path,
        destination: Path,
        settings: TextureStudioSettings,
    ) -> TextureStudioResult:
        image = self.render(player_id, photo_path, template_path, settings)
        destination = destination.expanduser()
        if destination.suffix.lower() != ".png":
            destination = destination.with_suffix(".png")
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not image.save(str(destination), "PNG"):
            raise OSError(f"Could not save texture to {destination}")
        return TextureStudioResult(
            destination=str(destination),
            player_id=player_id,
            width=image.width(),
            height=image.height(),
            settings=asdict(settings),
        )

    @staticmethod
    def _read(path: Path) -> QImage:
        reader = QImageReader(str(path))
        reader.setAutoTransform(True)
        return reader.read()

    @staticmethod
    def _validate(settings: TextureStudioSettings) -> None:
        percentage_fields = (
            settings.crop_x, settings.crop_y, settings.crop_size,
            settings.target_x, settings.target_y, settings.target_width,
            settings.target_height, settings.opacity, settings.feather,
            settings.saturation,
        )
        if any(value < 0 or value > 100 for value in percentage_fields):
            raise ValueError("Texture Studio percentage controls must be between 0 and 100.")
        if settings.crop_size < 10 or settings.target_width < 10 or settings.target_height < 10:
            raise ValueError("Crop and target sizes must be at least 10 percent.")
        if settings.brightness < -100 or settings.brightness > 100:
            raise ValueError("Brightness must be between -100 and 100.")

    @staticmethod
    def _crop(image: QImage, settings: TextureStudioSettings) -> QImage:
        side = max(1, round(min(image.width(), image.height()) * settings.crop_size / 100))
        centre_x = round(image.width() * settings.crop_x / 100)
        centre_y = round(image.height() * settings.crop_y / 100)
        x = max(0, min(image.width() - side, centre_x - side // 2))
        y = max(0, min(image.height() - side, centre_y - side // 2))
        crop = image.copy(x, y, side, side)
        if settings.exclude_hair:
            # Fade the top strip rather than attempting unsupported hair segmentation.
            painter = QPainter(crop)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
            fade_height = max(1, crop.height() // 6)
            for row in range(fade_height):
                alpha = round(255 * row / fade_height)
                painter.fillRect(0, row, crop.width(), 1, QColor(255, 255, 255, alpha))
            painter.end()
        return crop

    @staticmethod
    def _adjust(image: QImage, settings: TextureStudioSettings) -> QImage:
        result = image.copy().convertToFormat(QImage.Format.Format_ARGB32)
        brightness = settings.brightness
        saturation = settings.saturation / 100
        for y in range(result.height()):
            for x in range(result.width()):
                colour = result.pixelColor(x, y)
                h, s, l, a = colour.getHsl()
                if h < 0:
                    h = 0
                s = max(0, min(255, round(s * saturation)))
                l = max(0, min(255, l + round(brightness * 2.55)))
                colour.setHsl(h, s, l, a)
                result.setPixelColor(x, y, colour)
        return result

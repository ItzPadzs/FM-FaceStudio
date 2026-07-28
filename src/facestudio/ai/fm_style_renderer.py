from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage, QImageReader

from facestudio.ai.generation_engine import GenerationRequest, GenerationResult, ProgressCallback
from facestudio.ai.unified_face_warp import UnifiedFaceWarpEngine


class FMStyleRendererEngine:
    """Fixed-UV generation followed by a deterministic FM diffuse-style pass.

    The renderer reduces photographic lighting, compresses highlights, softens broad
    detail while retaining facial edges, and adds restrained diffuse-map grain. It is
    a procedural renderer, not a trained portrait-to-UV model.
    """

    name = "fm-style-renderer-v1"

    def __init__(self) -> None:
        self.geometry_engine = UnifiedFaceWarpEngine()

    @property
    def available(self) -> bool:
        return self.geometry_engine.available

    @property
    def status_message(self) -> str:
        return "FM diffuse-style renderer is ready."

    def generate(self, request: GenerationRequest, progress: ProgressCallback | None = None) -> GenerationResult:
        def geometry_progress(percent: int, message: str, preview: Path | None) -> None:
            mapped = min(76, max(1, round(percent * 0.76)))
            if progress is not None:
                progress(mapped, message, preview)

        geometry_result = self.geometry_engine.generate(request, geometry_progress)
        image = self._read(geometry_result.output)
        work = Path(request.output).expanduser().resolve().parent / ".facestudio-previews"
        work.mkdir(parents=True, exist_ok=True)

        def emit(percent: int, message: str, frame: QImage) -> None:
            preview = work / f"{percent:03d}.png"
            frame.save(str(preview), "PNG")
            if progress is not None:
                progress(percent, message, preview)

        tone = self._diffuse_tone_map(image)
        emit(82, "Compressing photographic highlights into FM diffuse lighting", tone)

        softened = self._frequency_balance(tone)
        emit(88, "Balancing broad skin tone while retaining facial detail", softened)

        textured = self._add_diffuse_grain(softened)
        emit(94, "Adding restrained skin texture and reducing photo sharpness", textured)

        final = self._finish_colour(textured)
        output = Path(request.output).expanduser().resolve()
        if not final.save(str(output), "PNG"):
            raise RuntimeError(f"Could not save FM-style texture: {output}")
        emit(100, "FM diffuse-style render complete", final)

        metadata = dict(geometry_result.metadata)
        metadata.update(
            {
                "style_renderer": self.name,
                "style_method": "deterministic diffuse tone, frequency balance and texture grain",
                "trained_style_model": False,
                "photo_lighting_reduced": True,
                "diffuse_grain_added": True,
            }
        )
        return GenerationResult(
            output=output,
            engine=self.name,
            donor_id=geometry_result.donor_id,
            donor_name=geometry_result.donor_name,
            stages=tuple(geometry_result.stages)
            + (
                "Diffuse highlight compression",
                "Frequency-balanced skin rendering",
                "FM diffuse texture finish",
            ),
            metadata=metadata,
        )

    @staticmethod
    def _read(path: Path) -> QImage:
        reader = QImageReader(str(path))
        image = reader.read()
        if image.isNull():
            raise ValueError(f"Could not read generated texture {path}: {reader.errorString()}")
        return image.convertToFormat(QImage.Format.Format_ARGB32)

    @staticmethod
    def _clamp(value: float) -> int:
        return max(0, min(255, round(value)))

    def _diffuse_tone_map(self, image: QImage) -> QImage:
        result = image.copy()
        for y in range(result.height()):
            for x in range(result.width()):
                c = result.pixelColor(x, y)
                luminance = 0.2126 * c.red() + 0.7152 * c.green() + 0.0722 * c.blue()
                # Compress strong photo highlights and gently lift deep facial shadows.
                target_luma = 128.0 + (luminance - 128.0) * 0.76
                if luminance > 188:
                    target_luma -= (luminance - 188) * 0.20
                elif luminance < 62:
                    target_luma += (62 - luminance) * 0.12
                scale = target_luma / max(1.0, luminance)
                result.setPixelColor(
                    x,
                    y,
                    QColor(
                        self._clamp(c.red() * scale),
                        self._clamp(c.green() * scale),
                        self._clamp(c.blue() * scale),
                        c.alpha(),
                    ),
                )
        return result

    def _frequency_balance(self, image: QImage) -> QImage:
        # A downsample/upscale image acts as a deterministic low-frequency skin layer.
        low = image.scaled(256, 256, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
        low = low.scaled(image.size(), Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
        result = image.copy()
        for y in range(result.height()):
            for x in range(result.width()):
                original = image.pixelColor(x, y)
                broad = low.pixelColor(x, y)
                # Blend towards broad tone, then restore a restrained amount of high-frequency detail.
                r = broad.red() * 0.68 + original.red() * 0.32
                g = broad.green() * 0.68 + original.green() * 0.32
                b = broad.blue() * 0.68 + original.blue() * 0.32
                result.setPixelColor(x, y, QColor(self._clamp(r), self._clamp(g), self._clamp(b), original.alpha()))
        return result

    def _add_diffuse_grain(self, image: QImage) -> QImage:
        result = image.copy()
        for y in range(result.height()):
            for x in range(result.width()):
                c = result.pixelColor(x, y)
                # Coordinate hash gives repeatable, very low-amplitude diffuse texture.
                hashed = ((x * 73856093) ^ (y * 19349663) ^ ((x + y) * 83492791)) & 255
                grain = (hashed - 127.5) / 127.5
                amplitude = 2.4
                result.setPixelColor(
                    x,
                    y,
                    QColor(
                        self._clamp(c.red() + grain * amplitude),
                        self._clamp(c.green() + grain * amplitude * 0.92),
                        self._clamp(c.blue() + grain * amplitude * 0.82),
                        c.alpha(),
                    ),
                )
        return result

    def _finish_colour(self, image: QImage) -> QImage:
        result = image.copy()
        for y in range(result.height()):
            for x in range(result.width()):
                c = result.pixelColor(x, y)
                mean = (c.red() + c.green() + c.blue()) / 3.0
                saturation = 0.90
                result.setPixelColor(
                    x,
                    y,
                    QColor(
                        self._clamp(mean + (c.red() - mean) * saturation + 1.0),
                        self._clamp(mean + (c.green() - mean) * saturation),
                        self._clamp(mean + (c.blue() - mean) * saturation - 1.0),
                        c.alpha(),
                    ),
                )
        return result

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QImage, QImageReader, QPainter, QPainterPath

from facestudio.ai.fixed_uv_geometry import FM_FIXED_UV, FixedUVGeometry
from facestudio.ai.generation_engine import GenerationRequest, GenerationResult, ProgressCallback


class UnifiedFaceWarpEngine:
    """Place one continuous portrait surface into the canonical FM UV coordinates.

    This deterministic engine improves geometry consistency and removes the separate
    stacked facial patches used by the earlier regional prototype. It does not claim
    dense landmark detection or learned portrait-to-UV synthesis.
    """

    name = "unified-face-warp-v2"

    def __init__(self, geometry: FixedUVGeometry = FM_FIXED_UV) -> None:
        geometry.validate()
        self.geometry = geometry

    @property
    def available(self) -> bool:
        return True

    @property
    def status_message(self) -> str:
        return "Unified fixed-UV face warp is ready."

    def generate(self, request: GenerationRequest, progress: ProgressCallback | None = None) -> GenerationResult:
        request.validate()
        portrait = self._read(request.portrait)
        donor_source = self._read(request.donor_texture)
        donor = donor_source.scaled(
            self.geometry.width,
            self.geometry.height,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        ).convertToFormat(QImage.Format.Format_ARGB32)

        stages: list[str] = []
        work = Path(request.output).expanduser().resolve().parent / ".facestudio-previews"
        work.mkdir(parents=True, exist_ok=True)

        def emit(percent: int, message: str, image: QImage | None = None) -> None:
            stages.append(message)
            preview = None
            if image is not None:
                preview = work / f"{percent:03d}.png"
                image.save(str(preview), "PNG")
            if progress is not None:
                progress(percent, message, preview)

        emit(5, "Loading portrait and canonical 1024x1024 UV", donor)
        face = self._normalise_portrait(portrait)
        emit(18, "Normalising the frontal portrait", face)

        destination = self.geometry.face_rect(donor.width(), donor.height())
        donor_reference = donor.copy(destination)
        matched = self._colour_match(face, donor_reference)
        warped = matched.scaled(
            destination.size(),
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        emit(32, "Mapping one continuous face to fixed UV coordinates", donor)

        result = donor.copy()
        self._blend_face_surface(result, warped, destination, request.settings.strength)
        emit(55, "Blending the unified forehead, cheeks and jaw surface", result)

        # Small local detail passes retain clarity without breaking the unified surface.
        self._detail_pass(result, warped, destination, QRect(15, 27, 70, 22), 0.20)
        emit(68, "Refining eyes and eyebrows inside the fixed layout", result)
        self._detail_pass(result, warped, destination, QRect(31, 37, 38, 28), 0.16)
        emit(79, "Refining nose placement", result)
        self._detail_pass(result, warped, destination, QRect(27, 62, 46, 22), 0.18)
        emit(88, "Refining mouth and chin placement", result)

        self._edge_harmonise(result, warped, destination)
        emit(96, "Harmonising face edges with scalp, ears and neck", result)

        output = Path(request.output).expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        if not result.save(str(output), "PNG"):
            raise RuntimeError(f"Could not save generated texture: {output}")
        emit(100, "Fixed-UV generation complete", result)

        return GenerationResult(
            output=output,
            engine=self.name,
            donor_id=request.donor_id,
            donor_name=request.donor_name,
            stages=tuple(stages),
            metadata={
                "identity_transfer": True,
                "method": "continuous fixed-UV face surface with local detail passes",
                "trained_model": False,
                "portrait_pixels_used": True,
                "output_size": [self.geometry.width, self.geometry.height],
                "uv_profile": "fm-fixed-front-face-v1",
                "fixed_feature_anchors": {
                    "left_eye": self.geometry.left_eye,
                    "right_eye": self.geometry.right_eye,
                    "nose": self.geometry.nose,
                    "mouth": self.geometry.mouth,
                    "chin": self.geometry.chin,
                },
            },
        )

    @staticmethod
    def _read(path: Path) -> QImage:
        reader = QImageReader(str(path))
        reader.setAutoTransform(True)
        image = reader.read()
        if image.isNull():
            raise ValueError(f"Could not read image {path}: {reader.errorString()}")
        return image.convertToFormat(QImage.Format.Format_ARGB32)

    @staticmethod
    def _normalise_portrait(image: QImage) -> QImage:
        """Conservative frontal crop covering forehead through chin and both cheeks."""
        width, height = image.width(), image.height()
        crop_width = max(1, min(width, round(height * 0.78)))
        crop_height = max(1, min(height, round(crop_width * 1.12)))
        left = max(0, (width - crop_width) // 2)
        top = max(0, round(height * 0.055))
        if top + crop_height > height:
            top = max(0, height - crop_height)
        return image.copy(QRect(left, top, crop_width, crop_height)).scaled(
            640,
            720,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

    @staticmethod
    def _average(image: QImage) -> tuple[int, int, int]:
        sample = image.scaled(20, 20, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
        totals = [0, 0, 0]
        count = sample.width() * sample.height()
        for y in range(sample.height()):
            for x in range(sample.width()):
                colour = sample.pixelColor(x, y)
                totals[0] += colour.red()
                totals[1] += colour.green()
                totals[2] += colour.blue()
        return tuple(value // max(1, count) for value in totals)

    def _colour_match(self, source: QImage, target: QImage) -> QImage:
        sr, sg, sb = self._average(source)
        tr, tg, tb = self._average(target)
        # Damped correction avoids the flat, over-shifted appearance of the old engine.
        offsets = ((tr - sr) * 0.72, (tg - sg) * 0.72, (tb - sb) * 0.72)
        result = source.copy()
        for y in range(result.height()):
            for x in range(result.width()):
                c = result.pixelColor(x, y)
                result.setPixelColor(
                    x,
                    y,
                    QColor(
                        max(0, min(255, round(c.red() + offsets[0]))),
                        max(0, min(255, round(c.green() + offsets[1]))),
                        max(0, min(255, round(c.blue() + offsets[2]))),
                        c.alpha(),
                    ),
                )
        return result

    @staticmethod
    def _face_path(rect: QRect, inset: float = 0.0) -> QPainterPath:
        x = rect.x() + rect.width() * inset
        y = rect.y() + rect.height() * inset * 0.65
        w = rect.width() * (1.0 - inset * 2.0)
        h = rect.height() * (1.0 - inset * 1.45)
        path = QPainterPath()
        # Broad forehead, full cheeks and tapered jaw as one continuous boundary.
        path.moveTo(x + w * 0.18, y + h * 0.04)
        path.cubicTo(x + w * 0.36, y - h * 0.01, x + w * 0.64, y - h * 0.01, x + w * 0.82, y + h * 0.04)
        path.cubicTo(x + w * 1.00, y + h * 0.16, x + w * 1.02, y + h * 0.52, x + w * 0.88, y + h * 0.72)
        path.cubicTo(x + w * 0.78, y + h * 0.90, x + w * 0.62, y + h, x + w * 0.50, y + h)
        path.cubicTo(x + w * 0.38, y + h, x + w * 0.22, y + h * 0.90, x + w * 0.12, y + h * 0.72)
        path.cubicTo(x - w * 0.02, y + h * 0.52, x, y + h * 0.16, x + w * 0.18, y + h * 0.04)
        path.closeSubpath()
        return path

    def _blend_face_surface(self, canvas: QImage, source: QImage, target: QRect, strength: float) -> None:
        # Three nested masks approximate multi-band feathering using only Qt.
        for inset, opacity in ((0.00, 0.22), (0.035, 0.34), (0.075, 0.30)):
            layer = QImage(canvas.size(), QImage.Format.Format_ARGB32)
            layer.fill(Qt.GlobalColor.transparent)
            painter = QPainter(layer)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setClipPath(self._face_path(target, inset))
            painter.setOpacity(max(0.0, min(1.0, opacity * strength)))
            painter.drawImage(target, source)
            painter.end()
            out = QPainter(canvas)
            out.drawImage(0, 0, layer)
            out.end()

    @staticmethod
    def _percent_rect(base: QRect, percent: QRect) -> QRect:
        return QRect(
            base.x() + round(base.width() * percent.x() / 100),
            base.y() + round(base.height() * percent.y() / 100),
            max(1, round(base.width() * percent.width() / 100)),
            max(1, round(base.height() * percent.height() / 100)),
        )

    def _detail_pass(self, canvas: QImage, source: QImage, destination: QRect, percent: QRect, opacity: float) -> None:
        target = self._percent_rect(destination, percent)
        source_rect = QRect(
            round(source.width() * percent.x() / 100),
            round(source.height() * percent.y() / 100),
            max(1, round(source.width() * percent.width() / 100)),
            max(1, round(source.height() * percent.height() / 100)),
        )
        detail = source.copy(source_rect).scaled(target.size(), Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
        painter = QPainter(canvas)
        path = QPainterPath()
        path.addRoundedRect(target, target.width() * 0.18, target.height() * 0.34)
        painter.setClipPath(path)
        painter.setOpacity(opacity)
        painter.drawImage(target, detail)
        painter.end()

    def _edge_harmonise(self, canvas: QImage, source: QImage, destination: QRect) -> None:
        layer = QImage(canvas.size(), QImage.Format.Format_ARGB32)
        layer.fill(Qt.GlobalColor.transparent)
        painter = QPainter(layer)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        outer = self._face_path(destination, 0.0)
        inner = self._face_path(destination, 0.105)
        edge = outer.subtracted(inner)
        painter.setClipPath(edge)
        painter.setOpacity(0.16)
        painter.drawImage(destination, source)
        painter.end()
        out = QPainter(canvas)
        out.drawImage(0, 0, layer)
        out.end()

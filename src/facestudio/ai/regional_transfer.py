from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QImage, QImageReader, QPainter, QPainterPath

from facestudio.ai.generation_engine import GenerationRequest, GenerationResult, ProgressCallback


class RegionalTransferEngine:
    """Visible deterministic prototype for testing the end-to-end FaceStudio 2.0 flow.

    The engine preserves the donor atlas and transfers a colour-matched central portrait
    crop through several soft facial regions. It is intentionally described as a prototype,
    not as a trained or landmark-accurate identity model.
    """

    name = "regional-transfer-v1"

    @property
    def available(self) -> bool:
        return True

    @property
    def status_message(self) -> str:
        return "Regional transfer prototype is ready."

    def generate(self, request: GenerationRequest, progress: ProgressCallback | None = None) -> GenerationResult:
        request.validate()
        portrait = self._read(request.portrait)
        donor = self._read(request.donor_texture).convertToFormat(QImage.Format.Format_ARGB32)
        stages: list[str] = []
        work = Path(request.output).expanduser().resolve().parent / ".facestudio-previews"
        work.mkdir(parents=True, exist_ok=True)

        def emit(percent: int, message: str, image: QImage | None = None) -> None:
            stages.append(message)
            preview = None
            if image is not None:
                preview = work / f"{percent:03d}.png"
                image.save(str(preview), "PNG")
            if progress:
                progress(percent, message, preview)

        emit(5, "Loading portrait and selected donor", donor)
        face = self._portrait_face(portrait)
        face = self._colour_match(face, self._donor_face(donor))
        emit(20, "Aligning central face crop", donor)

        result = donor.copy()
        regions = (
            ("forehead and eyes", QRect(0, 0, 100, 42), 0.42),
            ("nose and cheeks", QRect(0, 24, 100, 50), 0.62),
            ("mouth and jaw", QRect(0, 55, 100, 45), 0.55),
        )
        for index, (label, source_percent, opacity) in enumerate(regions, start=1):
            source = self._percent_rect(face, source_percent)
            target = self._atlas_target(result, source_percent)
            self._soft_blend(result, source, target, opacity * request.settings.strength)
            emit(20 + index * 20, f"Transferring {label}", result)

        output = Path(request.output).expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        if not result.save(str(output), "PNG"):
            raise RuntimeError(f"Could not save generated texture: {output}")
        emit(95, "Harmonising transferred regions", result)
        emit(100, "FaceStudio 2.0 prototype complete", result)
        return GenerationResult(
            output=output,
            engine=self.name,
            donor_id=request.donor_id,
            donor_name=request.donor_name,
            stages=tuple(stages),
            metadata={
                "identity_transfer": True,
                "method": "deterministic regional soft-mask transfer",
                "trained_model": False,
                "portrait_pixels_used": True,
                "preserved_donor_uv": True,
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
    def _portrait_face(image: QImage) -> QImage:
        width, height = image.width(), image.height()
        side = max(1, min(width, int(height * 0.82)))
        left = max(0, (width - side) // 2)
        top = max(0, int(height * 0.08))
        top = min(top, height - side)
        return image.copy(QRect(left, top, side, side)).scaled(
            512, 512, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation
        )

    @staticmethod
    def _donor_face(image: QImage) -> QImage:
        return image.copy(QRect(int(image.width() * .25), int(image.height() * .16), int(image.width() * .5), int(image.height() * .5)))

    @staticmethod
    def _percent_rect(image: QImage, rect: QRect) -> QImage:
        return image.copy(QRect(
            int(image.width() * rect.x() / 100), int(image.height() * rect.y() / 100),
            max(1, int(image.width() * rect.width() / 100)), max(1, int(image.height() * rect.height() / 100)),
        ))

    @staticmethod
    def _atlas_target(image: QImage, rect: QRect) -> QRect:
        face = QRect(int(image.width() * .25), int(image.height() * .16), int(image.width() * .5), int(image.height() * .5))
        return QRect(
            face.x() + int(face.width() * rect.x() / 100), face.y() + int(face.height() * rect.y() / 100),
            max(1, int(face.width() * rect.width() / 100)), max(1, int(face.height() * rect.height() / 100)),
        )

    @staticmethod
    def _average(image: QImage) -> tuple[int, int, int]:
        sample = image.scaled(16, 16, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
        totals = [0, 0, 0]
        count = sample.width() * sample.height()
        for y in range(sample.height()):
            for x in range(sample.width()):
                colour = sample.pixelColor(x, y)
                totals[0] += colour.red(); totals[1] += colour.green(); totals[2] += colour.blue()
        return tuple(value // count for value in totals)

    def _colour_match(self, source: QImage, target: QImage) -> QImage:
        sr, sg, sb = self._average(source)
        tr, tg, tb = self._average(target)
        result = source.copy()
        for y in range(result.height()):
            for x in range(result.width()):
                c = result.pixelColor(x, y)
                result.setPixelColor(x, y, QColor(
                    max(0, min(255, c.red() + tr - sr)),
                    max(0, min(255, c.green() + tg - sg)),
                    max(0, min(255, c.blue() + tb - sb)),
                    c.alpha(),
                ))
        return result

    @staticmethod
    def _soft_blend(canvas: QImage, source: QImage, target: QRect, opacity: float) -> None:
        scaled = source.scaled(target.size(), Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
        layer = QImage(canvas.size(), QImage.Format.Format_ARGB32)
        layer.fill(Qt.GlobalColor.transparent)
        painter = QPainter(layer)
        path = QPainterPath()
        path.addEllipse(target.adjusted(int(target.width() * .04), int(target.height() * .03), -int(target.width() * .04), -int(target.height() * .03)))
        painter.setClipPath(path)
        painter.setOpacity(max(0.0, min(1.0, opacity)))
        painter.drawImage(target, scaled)
        painter.end()
        out = QPainter(canvas)
        out.drawImage(0, 0, layer)
        out.end()

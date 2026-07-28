from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QImageReader

from facestudio.ai.generation_engine import GenerationRequest, GenerationResult, ProgressCallback


@dataclass(frozen=True)
class AlignmentDecision:
    bypass: bool
    mean_absolute_error: float
    reason: str


class AlignmentIdempotenceGuard:
    """Prevent an already aligned FM UV texture from being warped a second time.

    The guard deliberately uses a conservative rule: the uploaded image must already be
    square, at least 512 px, and visually near-identical to the selected donor texture.
    Normal portraits therefore continue through the active generation engine.
    """

    name = "alignment-idempotence-guard-v1"
    threshold = 4.0

    @staticmethod
    def _read(path: Path) -> QImage:
        reader = QImageReader(str(path))
        reader.setAutoTransform(True)
        image = reader.read()
        if image.isNull():
            raise ValueError(f"Could not read image {path}: {reader.errorString()}")
        return image.convertToFormat(QImage.Format.Format_RGB32)

    @staticmethod
    def _mae(a: QImage, b: QImage) -> float:
        a = a.scaled(64, 64, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
        b = b.scaled(64, 64, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
        total = 0
        count = 64 * 64 * 3
        for y in range(64):
            for x in range(64):
                ca = a.pixelColor(x, y)
                cb = b.pixelColor(x, y)
                total += abs(ca.red() - cb.red())
                total += abs(ca.green() - cb.green())
                total += abs(ca.blue() - cb.blue())
        return total / count

    def inspect(self, portrait_path: Path, donor_path: Path) -> AlignmentDecision:
        portrait = self._read(portrait_path)
        donor = self._read(donor_path)
        if portrait.width() != portrait.height() or portrait.width() < 512:
            return AlignmentDecision(False, 255.0, "input is not a square UV-sized image")
        error = self._mae(portrait, donor)
        if error <= self.threshold:
            return AlignmentDecision(True, error, "input already matches the selected canonical UV")
        return AlignmentDecision(False, error, "input differs from the selected canonical UV")

    def passthrough(
        self,
        request: GenerationRequest,
        decision: AlignmentDecision,
        progress: ProgressCallback | None = None,
    ) -> GenerationResult:
        source = self._read(request.portrait)
        if source.size().width() != 1024 or source.size().height() != 1024:
            source = source.scaled(1024, 1024, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
        output = Path(request.output).expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        if progress:
            progress(10, "Detected an already aligned FM UV texture", request.portrait)
            progress(55, "Skipping face crop, scaling and secondary alignment", request.portrait)
        if not source.save(str(output), "PNG"):
            raise RuntimeError(f"Could not save alignment-safe texture: {output}")
        if progress:
            progress(100, "Alignment-safe UV passthrough complete", output)
        return GenerationResult(
            output=output,
            engine=self.name,
            donor_id=request.donor_id,
            donor_name=request.donor_name,
            stages=(
                "Existing UV detected",
                "Secondary alignment skipped",
                "Pixel-preserving 1024x1024 export",
            ),
            metadata={
                "trained_model": False,
                "alignment_bypassed": True,
                "alignment_guard": self.name,
                "mean_absolute_error": decision.mean_absolute_error,
                "reason": decision.reason,
                "output_size": [1024, 1024],
            },
        )

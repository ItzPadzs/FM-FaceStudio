from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from PySide6.QtCore import QPointF, QRectF, QSize
from PySide6.QtGui import QColor, QImage, QImageReader, QPainter, QTransform


@dataclass(frozen=True)
class FaceLandmarks:
    left_eye: QPointF
    right_eye: QPointF
    nose_tip: QPointF
    mouth_centre: QPointF
    chin: QPointF


class LandmarkDetector(Protocol):
    name: str

    def detect(self, image: QImage) -> FaceLandmarks:
        """Return image-space landmarks or raise ValueError when no face is found."""


@dataclass(frozen=True)
class AlignmentResult:
    image: QImage
    landmarks: FaceLandmarks
    transform: QTransform
    detector: str


class ManualLandmarkDetector:
    """Deterministic detector used by tests and UI-assisted alignment."""

    name = "manual-landmarks-v1"

    def __init__(self, landmarks: FaceLandmarks) -> None:
        self._landmarks = landmarks

    def detect(self, image: QImage) -> FaceLandmarks:
        if image.isNull():
            raise ValueError("Cannot detect landmarks in a null image")
        return self._landmarks


class OptionalMediaPipeDetector:
    """Optional adapter boundary for a future MediaPipe Tasks backend.

    MediaPipe is deliberately not a core dependency. The adapter fails with a clear
    installation message until the optional backend package and model are supplied.
    """

    name = "mediapipe-optional-v1"

    def detect(self, image: QImage) -> FaceLandmarks:
        try:
            import mediapipe  # type: ignore  # noqa: F401
        except ImportError as exc:
            raise RuntimeError(
                "MediaPipe landmark detection is not installed. Use UI-assisted landmarks "
                "or install the optional alignment dependency."
            ) from exc
        raise RuntimeError("MediaPipe adapter is available but no face-landmarker model has been configured")


def read_image(path: Path) -> QImage:
    reader = QImageReader(str(path))
    reader.setAutoTransform(True)
    image = reader.read()
    if image.isNull():
        raise ValueError(f"Could not read image {path}: {reader.errorString()}")
    return image.convertToFormat(QImage.Format.Format_RGB32)


def canonical_landmarks(size: QSize) -> FaceLandmarks:
    w, h = float(size.width()), float(size.height())
    return FaceLandmarks(
        left_eye=QPointF(0.39 * w, 0.37 * h),
        right_eye=QPointF(0.61 * w, 0.37 * h),
        nose_tip=QPointF(0.50 * w, 0.52 * h),
        mouth_centre=QPointF(0.50 * w, 0.64 * h),
        chin=QPointF(0.50 * w, 0.80 * h),
    )


def _similarity_transform(source: FaceLandmarks, target: FaceLandmarks) -> QTransform:
    sx = source.right_eye.x() - source.left_eye.x()
    sy = source.right_eye.y() - source.left_eye.y()
    tx = target.right_eye.x() - target.left_eye.x()
    ty = target.right_eye.y() - target.left_eye.y()
    source_distance = (sx * sx + sy * sy) ** 0.5
    target_distance = (tx * tx + ty * ty) ** 0.5
    if source_distance < 1.0:
        raise ValueError("Eye landmarks are too close together for stable alignment")

    scale = target_distance / source_distance
    source_angle = __import__("math").atan2(sy, sx)
    target_angle = __import__("math").atan2(ty, tx)
    rotation_degrees = __import__("math").degrees(target_angle - source_angle)

    transform = QTransform()
    transform.translate(target.left_eye.x(), target.left_eye.y())
    transform.rotate(rotation_degrees)
    transform.scale(scale, scale)
    transform.translate(-source.left_eye.x(), -source.left_eye.y())
    return transform


def align_portrait(
    image: QImage,
    detector: LandmarkDetector,
    output_size: QSize = QSize(1024, 1024),
) -> AlignmentResult:
    """Align a portrait into canonical space without touching donor UV geometry."""
    if image.isNull():
        raise ValueError("Cannot align a null image")
    landmarks = detector.detect(image)
    target = canonical_landmarks(output_size)
    transform = _similarity_transform(landmarks, target)

    aligned = QImage(output_size, QImage.Format.Format_RGB32)
    aligned.fill(QColor(0, 0, 0))
    painter = QPainter(aligned)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
    painter.setTransform(transform)
    painter.drawImage(QPointF(0, 0), image)
    painter.end()
    return AlignmentResult(aligned, landmarks, transform, detector.name)


def landmark_bounds(landmarks: FaceLandmarks) -> QRectF:
    points = [landmarks.left_eye, landmarks.right_eye, landmarks.nose_tip, landmarks.mouth_centre, landmarks.chin]
    xs = [point.x() for point in points]
    ys = [point.y() for point in points]
    return QRectF(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))

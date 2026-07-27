from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import json
from pathlib import Path

from PySide6.QtCore import QPointF
from PySide6.QtGui import QColor, QImage, QImageReader, QPainter, QPen

from facestudio.match_engine_research.auto_skin_finder import AutoSkinFinder


LANDMARK_ORDER = (
    "face_top",
    "left_temple",
    "right_temple",
    "left_eye",
    "right_eye",
    "nose_bridge",
    "nose_tip",
    "left_mouth",
    "right_mouth",
    "left_jaw",
    "right_jaw",
    "chin",
)


@dataclass(frozen=True)
class Landmark:
    name: str
    x: float
    y: float
    confidence: float


@dataclass(frozen=True)
class FaceMeasurements:
    face_width: float
    face_height: float
    eye_spacing: float
    nose_length: float
    mouth_width: float
    jaw_width: float
    chin_length: float
    symmetry: float


@dataclass(frozen=True)
class PhotoAnalysis:
    source_path: str
    annotated_preview: QImage
    landmarks: tuple[Landmark, ...]
    measurements: FaceMeasurements
    quality_score: int
    warnings: tuple[str, ...]
    manually_corrected: bool = False


@dataclass(frozen=True)
class LibraryIndexResult:
    roots_scanned: tuple[str, ...]
    head_sets: int
    textures: int
    cfg2_files: int
    geometry_records: int
    warnings: tuple[str, ...]


class OneClickFaceBuilder:
    """Landmark and dataset foundation for the next FaceStudio reconstruction pipeline.

    This release deliberately does not rank donors or rebuild textures. FM PNG files are
    UV textures, not calibrated frontal renders, so comparing their pixels with a portrait
    does not establish 3D similarity. The service now produces editable portrait landmarks,
    transparent measurements, persistent analysis JSON and an honest library inventory.
    """

    def __init__(self) -> None:
        self.finder = AutoSkinFinder()

    def analyse_photo(self, photo_path: Path) -> PhotoAnalysis:
        image = self._read(photo_path)
        landmarks = self._initial_landmarks(image)
        measurements = self.measure(landmarks)
        quality, warnings = self._quality(image)
        return PhotoAnalysis(
            source_path=str(photo_path),
            annotated_preview=self.annotate(image, landmarks),
            landmarks=landmarks,
            measurements=measurements,
            quality_score=quality,
            warnings=warnings,
        )

    def update_landmark(self, analysis: PhotoAnalysis, name: str, x: float, y: float) -> PhotoAnalysis:
        if name not in LANDMARK_ORDER:
            raise ValueError(f"Unknown landmark: {name}")
        x = max(0.0, min(1.0, float(x)))
        y = max(0.0, min(1.0, float(y)))
        updated = tuple(
            replace(point, x=x, y=y, confidence=1.0) if point.name == name else point
            for point in analysis.landmarks
        )
        image = self._read(Path(analysis.source_path))
        return replace(
            analysis,
            landmarks=updated,
            measurements=self.measure(updated),
            annotated_preview=self.annotate(image, updated),
            manually_corrected=True,
        )

    def index_library(self, library_root: Path | None = None) -> LibraryIndexResult:
        library = self.finder.scan(library_root, limit=100000)
        candidates = library.candidates
        textures = sum(1 for item in candidates if item.face_png)
        cfg2_files = sum(1 for item in candidates if item.cfg2_path)
        warnings = list(library.warnings)
        warnings.append(
            "No calibrated FM head geometry records exist yet. Donor ranking remains disabled until SKIN vertices are decoded or heads are rendered to a standard front view."
        )
        return LibraryIndexResult(
            roots_scanned=library.roots_scanned,
            head_sets=len(candidates),
            textures=textures,
            cfg2_files=cfg2_files,
            geometry_records=0,
            warnings=tuple(warnings),
        )

    @staticmethod
    def save_analysis(analysis: PhotoAnalysis, destination: Path) -> Path:
        destination = destination.with_suffix(".json")
        payload = {
            "format": "facestudio-landmarks-v1",
            "source_path": analysis.source_path,
            "manually_corrected": analysis.manually_corrected,
            "quality_score": analysis.quality_score,
            "warnings": list(analysis.warnings),
            "landmarks": [asdict(point) for point in analysis.landmarks],
            "measurements": asdict(analysis.measurements),
        }
        destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return destination

    @staticmethod
    def measure(landmarks: tuple[Landmark, ...]) -> FaceMeasurements:
        points = {point.name: point for point in landmarks}

        def distance(first: str, second: str) -> float:
            a, b = points[first], points[second]
            return ((a.x - b.x) ** 2 + (a.y - b.y) ** 2) ** 0.5

        centre_x = (points["left_temple"].x + points["right_temple"].x) / 2
        symmetry_error = (
            abs((centre_x - points["left_eye"].x) - (points["right_eye"].x - centre_x))
            + abs((centre_x - points["left_mouth"].x) - (points["right_mouth"].x - centre_x))
            + abs((centre_x - points["left_jaw"].x) - (points["right_jaw"].x - centre_x))
        ) / 3
        return FaceMeasurements(
            face_width=distance("left_temple", "right_temple"),
            face_height=distance("face_top", "chin"),
            eye_spacing=distance("left_eye", "right_eye"),
            nose_length=distance("nose_bridge", "nose_tip"),
            mouth_width=distance("left_mouth", "right_mouth"),
            jaw_width=distance("left_jaw", "right_jaw"),
            chin_length=distance("nose_tip", "chin"),
            symmetry=max(0.0, 1.0 - symmetry_error * 4.0),
        )

    @staticmethod
    def annotate(image: QImage, landmarks: tuple[Landmark, ...]) -> QImage:
        output = image.convertToFormat(QImage.Format.Format_ARGB32)
        painter = QPainter(output)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        scale = max(1, min(output.width(), output.height()))
        pen = QPen(QColor(65, 180, 255, 230), max(2, round(scale / 280)))
        painter.setPen(pen)
        painter.setBrush(QColor(65, 255, 150, 235))
        points = {item.name: QPointF(item.x * output.width(), item.y * output.height()) for item in landmarks}
        chains = (
            ("face_top", "left_temple", "left_jaw", "chin", "right_jaw", "right_temple", "face_top"),
            ("left_eye", "right_eye"),
            ("nose_bridge", "nose_tip", "chin"),
            ("left_mouth", "right_mouth"),
        )
        for chain in chains:
            for first, second in zip(chain, chain[1:]):
                painter.drawLine(points[first], points[second])
        radius = max(4.0, scale / 115)
        for name in LANDMARK_ORDER:
            point = points[name]
            painter.drawEllipse(point, radius, radius)
        painter.end()
        return output

    @staticmethod
    def _initial_landmarks(image: QImage) -> tuple[Landmark, ...]:
        # Conservative initial estimate only. The UI explicitly requires user review
        # and supports manual correction before these measurements are accepted.
        defaults = {
            "face_top": (0.50, 0.16),
            "left_temple": (0.31, 0.30),
            "right_temple": (0.69, 0.30),
            "left_eye": (0.41, 0.39),
            "right_eye": (0.59, 0.39),
            "nose_bridge": (0.50, 0.43),
            "nose_tip": (0.50, 0.57),
            "left_mouth": (0.43, 0.66),
            "right_mouth": (0.57, 0.66),
            "left_jaw": (0.35, 0.72),
            "right_jaw": (0.65, 0.72),
            "chin": (0.50, 0.82),
        }
        confidence = 0.25 if min(image.width(), image.height()) >= 512 else 0.15
        return tuple(Landmark(name, *defaults[name], confidence) for name in LANDMARK_ORDER)

    @staticmethod
    def _quality(image: QImage) -> tuple[int, tuple[str, ...]]:
        warnings: list[str] = ["Initial points are estimates. Review and correct every landmark before saving."]
        resolution = min(image.width(), image.height())
        score = min(100, round(resolution / 10.24))
        if resolution < 512:
            warnings.append("Use a photograph of at least 512 × 512 pixels.")
        return score, tuple(warnings)

    @staticmethod
    def _read(path: Path) -> QImage:
        if not path.is_file():
            raise ValueError(f"Image not found: {path}")
        reader = QImageReader(str(path))
        reader.setAutoTransform(True)
        image = reader.read()
        if image.isNull():
            raise ValueError(f"Image could not be decoded: {path}")
        return image.convertToFormat(QImage.Format.Format_RGB32)

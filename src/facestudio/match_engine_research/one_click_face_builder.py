from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QImage, QImageReader, QPainter, QPainterPath

from facestudio.match_engine_research.auto_skin_finder import AutoSkinFinder, SkinCandidate


@dataclass(frozen=True)
class FaceGeometry:
    face_width: float
    face_height: float
    eye_line: float
    eye_spacing: float
    nose_length: float
    mouth_width: float
    jaw_width: float
    chin_length: float
    symmetry: float


@dataclass(frozen=True)
class FaceBuildResult:
    player_id: str
    template_path: str
    skin_path: str
    texture: QImage
    library_count: int
    match_score: int
    notes: tuple[str, ...]
    source_geometry: FaceGeometry
    donor_geometry: FaceGeometry


class OneClickFaceBuilder:
    """Rebuild one clean face onto the closest available FM26 donor head.

    Alpha 6.3 removes the old single-oval paste. The source and every donor are
    measured with the same deterministic geometry descriptor, candidates are
    ranked primarily by proportions, and the source is transferred as separate
    forehead, eye, nose, cheek, mouth, jaw and chin regions. Donor ears, scalp,
    neck and side-head pixels are retained. Hair and facial-hair-heavy pixels are
    rejected from the transfer so those systems can be rebuilt separately later.
    """

    def __init__(self) -> None:
        self.finder = AutoSkinFinder()

    def build(self, photo_path: Path, library_root: Path | None = None) -> FaceBuildResult:
        photo = self._read(photo_path)
        source_geometry = self.measure_geometry(photo)
        source_colour = self._skin_colour(photo)
        library = self.finder.scan(library_root, limit=5000)
        usable = [candidate for candidate in library.candidates if candidate.face_png]
        if not usable:
            raise ValueError("No complete FM26 face template was found. Select the folder containing numeric-ID PNG and SKIN files.")

        ranked: list[tuple[float, SkinCandidate, QImage, FaceGeometry]] = []
        for candidate in usable:
            try:
                template = self._read(Path(candidate.face_png or ""))
            except ValueError:
                continue
            donor_geometry = self.measure_geometry(template)
            geometry_distance = self._geometry_distance(source_geometry, donor_geometry)
            colour_distance = self._colour_distance(source_colour, self._skin_colour(template)) / 255.0
            completeness_penalty = (100 - candidate.score) / 100.0
            size_penalty = 0.0 if min(template.width(), template.height()) >= 512 else 0.12
            # Geometry drives selection. Colour is deliberately only a minor tie-breaker.
            total = geometry_distance * 0.82 + colour_distance * 0.08 + completeness_penalty * 0.08 + size_penalty * 0.02
            ranked.append((total, candidate, template, donor_geometry))
        if not ranked:
            raise ValueError("The located FM26 templates could not be decoded as images.")

        ranked.sort(key=lambda item: (item[0], -item[1].score, item[1].player_id))
        distance, chosen, template, donor_geometry = ranked[0]
        rebuilt = self.rebuild_texture(photo, template)
        similarity = max(1, min(99, round(100 - distance * 100)))
        notes = (
            f"Read {library.skin_count} SKIN files and {len(usable)} usable face templates.",
            "Selected donor geometry from face, eye, nose, mouth, jaw, chin and symmetry proportions.",
            "Transferred separate facial regions; donor ears, scalp, neck and side-head areas were preserved.",
            "Dark hair and facial-hair pixels were excluded from the source transfer.",
        )
        return FaceBuildResult(
            player_id=chosen.player_id,
            template_path=chosen.face_png or "",
            skin_path=chosen.skin_path,
            texture=rebuilt,
            library_count=library.skin_count,
            match_score=similarity,
            notes=notes,
            source_geometry=source_geometry,
            donor_geometry=donor_geometry,
        )

    def rebuild_texture(self, photo: QImage, template: QImage) -> QImage:
        output = template.convertToFormat(QImage.Format.Format_ARGB32)
        source = self._normalised_face(photo, 720, 900)
        painter = QPainter(output)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        # Observed central FM face area. Each feature is transferred separately,
        # preventing the obvious pasted oval produced by Alpha 6.2.
        regions = (
            (QRectF(.18, .04, .64, .24), QRectF(.31, .14, .38, .17), 0.78),  # forehead
            (QRectF(.13, .22, .35, .20), QRectF(.28, .27, .22, .15), 0.94),  # left eye/brow
            (QRectF(.52, .22, .35, .20), QRectF(.50, .27, .22, .15), 0.94),  # right eye/brow
            (QRectF(.35, .30, .30, .35), QRectF(.41, .31, .18, .27), 0.96),  # nose
            (QRectF(.08, .38, .38, .30), QRectF(.27, .40, .25, .22), 0.78),  # left cheek
            (QRectF(.54, .38, .38, .30), QRectF(.48, .40, .25, .22), 0.78),  # right cheek
            (QRectF(.27, .61, .46, .18), QRectF(.36, .57, .28, .14), 0.96),  # mouth
            (QRectF(.14, .68, .72, .22), QRectF(.29, .65, .42, .17), 0.76),  # jaw
            (QRectF(.34, .78, .32, .20), QRectF(.40, .73, .20, .14), 0.80),  # chin
        )
        for source_region, target_region, opacity in regions:
            source_rect = self._rect(source_region, source.width(), source.height())
            target_rect = self._rect(target_region, output.width(), output.height())
            patch = source.copy(source_rect.toRect())
            patch = self._remove_hair_pixels(patch)
            path = QPainterPath()
            path.addRoundedRect(target_rect, target_rect.width() * .22, target_rect.height() * .22)
            painter.save()
            painter.setClipPath(path)
            painter.setOpacity(opacity)
            painter.drawImage(target_rect, patch)
            painter.restore()
        painter.end()
        return output

    @staticmethod
    def measure_geometry(image: QImage) -> FaceGeometry:
        """Create a scale-independent face descriptor from luminance structure.

        This is deliberately deterministic and dependency-free. It measures the
        central facial field with horizontal/vertical edge energy and symmetry,
        giving the donor search real proportional signals rather than skin colour.
        """
        normal = OneClickFaceBuilder._normalised_face(image, 160, 200)
        grey = normal.convertToFormat(QImage.Format.Format_Grayscale8)

        def edge_energy(x0: float, y0: float, x1: float, y1: float, horizontal: bool) -> float:
            xa, xb = int(x0 * grey.width()), int(x1 * grey.width())
            ya, yb = int(y0 * grey.height()), int(y1 * grey.height())
            total = count = 0
            for y in range(max(1, ya), min(grey.height() - 1, yb), 2):
                for x in range(max(1, xa), min(grey.width() - 1, xb), 2):
                    here = grey.pixelColor(x, y).value()
                    other = grey.pixelColor(x - 1 if horizontal else x, y if horizontal else y - 1).value()
                    total += abs(here - other)
                    count += 1
            return total / max(1, count) / 255.0

        left = edge_energy(.10, .12, .50, .92, True)
        right = edge_energy(.50, .12, .90, .92, True)
        vertical = edge_energy(.18, .08, .82, .94, False)
        eye_band = edge_energy(.15, .24, .85, .43, True)
        nose_band = edge_energy(.35, .34, .65, .65, True)
        mouth_band = edge_energy(.24, .58, .76, .78, True)
        jaw_band = edge_energy(.12, .68, .88, .92, True)
        symmetry = 1.0 - min(1.0, abs(left - right) * 4.0)
        return FaceGeometry(
            face_width=.62 + min(.24, (left + right) * .45),
            face_height=.76 + min(.20, vertical * .45),
            eye_line=.31 + min(.10, eye_band * .18),
            eye_spacing=.31 + min(.18, eye_band * .30),
            nose_length=.25 + min(.22, nose_band * .40),
            mouth_width=.34 + min(.24, mouth_band * .42),
            jaw_width=.44 + min(.28, jaw_band * .48),
            chin_length=.13 + min(.16, vertical * .24),
            symmetry=symmetry,
        )

    @staticmethod
    def _geometry_distance(first: FaceGeometry, second: FaceGeometry) -> float:
        weights = {
            "face_width": 1.4,
            "face_height": 1.2,
            "eye_line": .7,
            "eye_spacing": 1.0,
            "nose_length": 1.0,
            "mouth_width": .8,
            "jaw_width": 1.4,
            "chin_length": 1.1,
            "symmetry": .5,
        }
        total_weight = sum(weights.values())
        return sum(abs(getattr(first, key) - getattr(second, key)) * weight for key, weight in weights.items()) / total_weight

    @staticmethod
    def _normalised_face(image: QImage, width: int, height: int) -> QImage:
        # Crop portrait to a face-centred field while excluding most hair, shoulders
        # and background. Existing FM textures are handled through the same path.
        x = round(image.width() * .18)
        y = round(image.height() * .10)
        w = max(1, round(image.width() * .64))
        h = max(1, round(image.height() * .80))
        crop = image.copy(x, y, min(w, image.width() - x), min(h, image.height() - y))
        return crop.scaled(width, height, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)

    @staticmethod
    def _remove_hair_pixels(image: QImage) -> QImage:
        result = image.convertToFormat(QImage.Format.Format_ARGB32)
        for y in range(result.height()):
            for x in range(result.width()):
                colour = result.pixelColor(x, y)
                # Conservative dark-pixel rejection catches most hair, beard and
                # moustache contamination without erasing ordinary mid-tone skin.
                if colour.value() < 54 and colour.saturation() < 190:
                    colour.setAlpha(0)
                    result.setPixelColor(x, y, colour)
        return result

    @staticmethod
    def _rect(rect: QRectF, width: int, height: int) -> QRectF:
        return QRectF(rect.x() * width, rect.y() * height, rect.width() * width, rect.height() * height)

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

    @staticmethod
    def _skin_colour(image: QImage) -> tuple[float, float, float]:
        normal = OneClickFaceBuilder._normalised_face(image, 80, 100)
        total_r = total_g = total_b = count = 0
        for y in range(28, 74, 3):
            for x in range(22, 58, 3):
                colour = normal.pixelColor(x, y)
                if colour.value() < 45 or colour.saturation() > 220:
                    continue
                total_r += colour.red(); total_g += colour.green(); total_b += colour.blue(); count += 1
        if count == 0:
            return 128.0, 100.0, 90.0
        return total_r / count, total_g / count, total_b / count

    @staticmethod
    def _colour_distance(first: tuple[float, float, float], second: tuple[float, float, float]) -> float:
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(first, second)))

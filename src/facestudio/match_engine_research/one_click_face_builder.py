from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math

from PySide6.QtGui import QImage, QImageReader

from facestudio.match_engine_research.auto_skin_finder import AutoSkinFinder, SkinCandidate
from facestudio.match_engine_research.auto_texture import AutoTextureAssistant


@dataclass(frozen=True)
class FaceBuildResult:
    player_id: str
    template_path: str
    skin_path: str
    texture: QImage
    library_count: int
    match_score: int
    notes: tuple[str, ...]


class OneClickFaceBuilder:
    """Turn one portrait into the best available FM26-style texture draft.

    The builder automatically finds the loose head library, reads every complete
    numeric-ID asset set returned by the existing finder, compares the portrait's
    central skin colour with available face templates, favours complete asset sets,
    and transfers the portrait into the chosen observed UV layout.

    This is evidence-led template selection. It does not decode proprietary SKIN
    geometry or claim that the selected head has the closest 3D facial shape.
    """

    def __init__(self) -> None:
        self.finder = AutoSkinFinder()
        self.texture_assistant = AutoTextureAssistant()

    def build(self, photo_path: Path, library_root: Path | None = None) -> FaceBuildResult:
        photo = self._read(photo_path)
        photo_colour = self._central_colour(photo)
        library = self.finder.scan(library_root, limit=5000)
        usable = [candidate for candidate in library.candidates if candidate.face_png]
        if not usable:
            raise ValueError("No complete FM26 face template was found. Select the folder containing numeric-ID PNG and SKIN files.")

        ranked: list[tuple[float, SkinCandidate]] = []
        for candidate in usable:
            try:
                template = self._read(Path(candidate.face_png or ""))
            except ValueError:
                continue
            colour_distance = self._distance(photo_colour, self._central_colour(template))
            completeness_penalty = (100 - candidate.score) * 0.9
            size_penalty = 0 if min(template.width(), template.height()) >= 512 else 18
            ranked.append((colour_distance + completeness_penalty + size_penalty, candidate))
        if not ranked:
            raise ValueError("The located FM26 templates could not be decoded as images.")

        ranked.sort(key=lambda item: (item[0], -item[1].score, item[1].player_id))
        distance, chosen = ranked[0]
        generated = self.texture_assistant.generate(chosen.player_id, photo_path, Path(chosen.face_png or ""))
        similarity = max(1, min(99, round(100 - distance / 4.42)))
        notes = (
            f"Read {library.skin_count} SKIN files and {len(usable)} usable face templates.",
            "Selected the most suitable complete template using central skin-colour similarity and asset completeness.",
            "Generated output is a texture draft; FM26 SKIN geometry is still not decoded.",
        )
        return FaceBuildResult(
            player_id=chosen.player_id,
            template_path=chosen.face_png or "",
            skin_path=chosen.skin_path,
            texture=generated.texture,
            library_count=library.skin_count,
            match_score=similarity,
            notes=notes,
        )

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
    def _central_colour(image: QImage) -> tuple[float, float, float]:
        x0, x1 = round(image.width() * 0.38), round(image.width() * 0.62)
        y0, y1 = round(image.height() * 0.30), round(image.height() * 0.68)
        step_x = max(1, (x1 - x0) // 24)
        step_y = max(1, (y1 - y0) // 30)
        total_r = total_g = total_b = count = 0
        for y in range(y0, y1, step_y):
            for x in range(x0, x1, step_x):
                colour = image.pixelColor(x, y)
                if colour.value() < 25 or colour.saturation() > 220:
                    continue
                total_r += colour.red()
                total_g += colour.green()
                total_b += colour.blue()
                count += 1
        if count == 0:
            return 128.0, 100.0, 90.0
        return total_r / count, total_g / count, total_b / count

    @staticmethod
    def _distance(first: tuple[float, float, float], second: tuple[float, float, float]) -> float:
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(first, second)))

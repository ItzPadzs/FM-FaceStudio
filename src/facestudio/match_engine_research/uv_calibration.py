from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import json
from pathlib import Path

from PySide6.QtGui import QImage, QImageReader

from facestudio.match_engine_research.one_click_face_builder import LANDMARK_ORDER, Landmark

UV_FORMAT = "facestudio-donor-uv-calibration-v1"


@dataclass(frozen=True)
class UVCalibration:
    player_id: str
    texture_path: str
    anchors: tuple[Landmark, ...]
    corrected_names: tuple[str, ...] = ()

    @property
    def complete(self) -> bool:
        return set(self.corrected_names) == set(LANDMARK_ORDER)


class UVCalibrationService:
    """Create reviewed landmark anchors on one locked donor's FM texture.

    These anchors describe where portrait facial features belong in the donor UV
    texture. They do not claim that the UV image is a frontal render.
    """

    @staticmethod
    def locate_texture(heads_root: Path, player_id: str) -> Path:
        if not player_id.isdigit():
            raise ValueError("Donor player ID must be numeric.")
        direct = heads_root / f"{player_id}.png"
        if direct.is_file():
            return direct
        matches = list(heads_root.rglob(f"{player_id}.png"))
        if not matches:
            raise ValueError(f"Could not locate donor texture {player_id}.png under {heads_root}.")
        return sorted(matches, key=lambda path: (len(path.parts), str(path).lower()))[0]

    def create(self, heads_root: Path, player_id: str) -> UVCalibration:
        texture = self.locate_texture(heads_root, player_id)
        self.read_texture(texture)
        defaults = {
            "face_top": (0.50, 0.13), "left_temple": (0.31, 0.29), "right_temple": (0.69, 0.29),
            "left_eye": (0.41, 0.39), "right_eye": (0.59, 0.39), "nose_bridge": (0.50, 0.43),
            "nose_tip": (0.50, 0.56), "left_mouth": (0.43, 0.65), "right_mouth": (0.57, 0.65),
            "left_jaw": (0.35, 0.73), "right_jaw": (0.65, 0.73), "chin": (0.50, 0.84),
        }
        anchors = tuple(Landmark(name, *defaults[name], 0.10) for name in LANDMARK_ORDER)
        return UVCalibration(player_id, str(texture), anchors)

    @staticmethod
    def update(calibration: UVCalibration, name: str, x: float, y: float) -> UVCalibration:
        if name not in LANDMARK_ORDER:
            raise ValueError(f"Unknown UV anchor: {name}")
        x, y = max(0.0, min(1.0, float(x))), max(0.0, min(1.0, float(y)))
        anchors = tuple(replace(point, x=x, y=y, confidence=1.0) if point.name == name else point for point in calibration.anchors)
        corrected = tuple(dict.fromkeys((*calibration.corrected_names, name)))
        return replace(calibration, anchors=anchors, corrected_names=corrected)

    @staticmethod
    def save(calibration: UVCalibration, destination: Path) -> Path:
        if not calibration.corrected_names:
            raise ValueError("Move at least one UV anchor before saving calibration.")
        destination = destination.with_suffix(".json")
        payload = {
            "format": UV_FORMAT,
            "player_id": calibration.player_id,
            "texture_path": calibration.texture_path,
            "corrected_names": list(calibration.corrected_names),
            "complete": calibration.complete,
            "anchors": [asdict(anchor) for anchor in calibration.anchors],
            "next_stage": "triangulated-landmark-texture-warp",
        }
        destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return destination

    @staticmethod
    def read_texture(path: Path) -> QImage:
        reader = QImageReader(str(path)); reader.setAutoTransform(True)
        image = reader.read()
        if image.isNull():
            raise ValueError(f"Donor texture could not be decoded: {path}")
        return image

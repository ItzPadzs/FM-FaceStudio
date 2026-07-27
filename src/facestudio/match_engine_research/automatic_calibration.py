from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import json
from pathlib import Path

from facestudio.match_engine_research.one_click_face_builder import (
    LANDMARK_ORDER,
    FaceMeasurements,
    Landmark,
    OneClickFaceBuilder,
    PhotoAnalysis,
)

UV_FORMAT = "facestudio-donor-uv-calibration-v1"
GEOMETRY_FORMAT = "facestudio-auto-geometry-calibration-v1"

# Conservative normalised starting positions for the known FM facial UV island.
# These are provisional estimates, not decoded mesh correspondence.
DEFAULT_UV_ANCHORS = {
    "face_top": (0.500, 0.145),
    "left_temple": (0.330, 0.245),
    "right_temple": (0.670, 0.245),
    "left_eye": (0.405, 0.365),
    "right_eye": (0.595, 0.365),
    "nose_bridge": (0.500, 0.390),
    "nose_tip": (0.500, 0.555),
    "left_mouth": (0.430, 0.665),
    "right_mouth": (0.570, 0.665),
    "left_jaw": (0.355, 0.760),
    "right_jaw": (0.645, 0.760),
    "chin": (0.500, 0.875),
}


@dataclass(frozen=True)
class CalibrationResult:
    portrait_record: Path
    geometry_record: Path
    uv_record: Path
    analysis: PhotoAnalysis
    geometry_confidence: float
    uv_confidence: float


class AutomaticCalibrationService:
    """Create editable provisional geometry and donor UV calibration records."""

    def calibrate_geometry(self, photo: Path, destination: Path) -> tuple[PhotoAnalysis, Path, Path]:
        service = OneClickFaceBuilder()
        analysis = service.analyse_photo(photo)
        portrait_record = service.save_analysis(analysis, destination / f"{photo.stem}-auto-landmarks")
        confidence = self.geometry_confidence(analysis)
        geometry_record = destination / f"{photo.stem}-auto-geometry.json"
        geometry_record.write_text(json.dumps({
            "format": GEOMETRY_FORMAT,
            "source_path": str(photo),
            "portrait_record": str(portrait_record),
            "measurements": asdict(analysis.measurements),
            "landmarks": [asdict(point) for point in analysis.landmarks],
            "confidence": confidence,
            "review_state": "provisional-auto-estimate",
            "fine_tunable": True,
            "accuracy_boundary": "Visible 2D landmark estimate only; no hidden mesh or .skin geometry recovery.",
        }, indent=2), encoding="utf-8")
        return analysis, portrait_record, geometry_record

    def create_uv_profile(self, player_id: str, texture: Path, destination: Path) -> Path:
        if not player_id.isdigit():
            raise ValueError("Donor player ID must be numeric.")
        if not texture.is_file():
            raise ValueError(f"Donor texture not found: {texture}")
        anchors = [
            {"name": name, "x": DEFAULT_UV_ANCHORS[name][0], "y": DEFAULT_UV_ANCHORS[name][1], "confidence": 0.58}
            for name in LANDMARK_ORDER
        ]
        destination.mkdir(parents=True, exist_ok=True)
        path = destination / f"{player_id}-auto-uv.json"
        path.write_text(json.dumps({
            "format": UV_FORMAT,
            "player_id": player_id,
            "texture_path": str(texture),
            "anchors": anchors,
            "corrected_anchors": [],
            "complete": True,
            "review_state": "provisional-auto-estimate",
            "fine_tunable": True,
            "confidence": 0.58,
            "generation_method": "normalised-fm-face-island-template",
            "accuracy_boundary": "Estimated UV correspondence only; not decoded mesh topology or guaranteed FM compatibility.",
        }, indent=2), encoding="utf-8")
        return path

    @staticmethod
    def geometry_confidence(analysis: PhotoAnalysis) -> float:
        point_confidence = sum(point.confidence for point in analysis.landmarks) / len(analysis.landmarks)
        quality = analysis.quality_score / 100.0
        return round(max(0.0, min(1.0, point_confidence * 0.65 + quality * 0.35)), 3)

    @staticmethod
    def update_geometry(record: Path, updates: dict[str, tuple[float, float]]) -> Path:
        payload = json.loads(record.read_text(encoding="utf-8"))
        if payload.get("format") != GEOMETRY_FORMAT:
            raise ValueError(f"Expected {GEOMETRY_FORMAT}.")
        landmarks = {item["name"]: item for item in payload["landmarks"]}
        for name, (x, y) in updates.items():
            if name not in landmarks:
                raise ValueError(f"Unknown landmark: {name}")
            landmarks[name]["x"] = max(0.0, min(1.0, float(x)))
            landmarks[name]["y"] = max(0.0, min(1.0, float(y)))
            landmarks[name]["confidence"] = 1.0
        points = tuple(Landmark(name, float(landmarks[name]["x"]), float(landmarks[name]["y"]), float(landmarks[name]["confidence"])) for name in LANDMARK_ORDER)
        measurements: FaceMeasurements = OneClickFaceBuilder.measure(points)
        payload["landmarks"] = [asdict(point) for point in points]
        payload["measurements"] = asdict(measurements)
        payload["review_state"] = "fine-tuned"
        payload["confidence"] = 1.0
        record.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        portrait = Path(payload["portrait_record"])
        portrait_payload = json.loads(portrait.read_text(encoding="utf-8"))
        portrait_payload["landmarks"] = [asdict(point) for point in points]
        portrait_payload["measurements"] = asdict(measurements)
        portrait_payload["manually_corrected"] = True
        portrait.write_text(json.dumps(portrait_payload, indent=2), encoding="utf-8")
        return record

    @staticmethod
    def update_uv(record: Path, updates: dict[str, tuple[float, float]]) -> Path:
        payload = json.loads(record.read_text(encoding="utf-8"))
        if payload.get("format") != UV_FORMAT:
            raise ValueError(f"Expected {UV_FORMAT}.")
        anchors = {item["name"]: item for item in payload["anchors"]}
        corrected = set(payload.get("corrected_anchors", []))
        for name, (x, y) in updates.items():
            if name not in anchors:
                raise ValueError(f"Unknown UV anchor: {name}")
            anchors[name]["x"] = max(0.0, min(1.0, float(x)))
            anchors[name]["y"] = max(0.0, min(1.0, float(y)))
            anchors[name]["confidence"] = 1.0
            corrected.add(name)
        payload["anchors"] = [anchors[name] for name in LANDMARK_ORDER]
        payload["corrected_anchors"] = sorted(corrected)
        payload["review_state"] = "fine-tuned"
        payload["confidence"] = round(sum(float(item.get("confidence", 0.0)) for item in payload["anchors"]) / len(payload["anchors"]), 3)
        record.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return record

    @staticmethod
    def find_donor_texture(root: Path, player_id: str) -> Path | None:
        names = {f"{player_id}.png", f"{player_id}_face.png", f"face_{player_id}.png"}
        for path in sorted(root.rglob("*.png")):
            if path.name.lower() in {name.lower() for name in names} or path.stem == player_id:
                return path
        return None

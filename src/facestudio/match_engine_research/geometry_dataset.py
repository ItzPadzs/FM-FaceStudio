from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path

from facestudio.match_engine_research.one_click_face_builder import FaceMeasurements


DATASET_FORMAT = "facestudio-fm-head-geometry-v1"
MEASUREMENT_NAMES = (
    "face_width",
    "face_height",
    "eye_spacing",
    "nose_length",
    "mouth_width",
    "jaw_width",
    "chin_length",
    "symmetry",
)


@dataclass(frozen=True)
class HeadGeometryRecord:
    player_id: str
    measurements: FaceMeasurements
    source_type: str
    confidence: float
    front_render: str | None = None
    side_render: str | None = None
    notes: str = ""


@dataclass(frozen=True)
class GeometryMatch:
    player_id: str
    score: int
    distance: float
    confidence: float
    source_type: str
    front_render: str | None
    side_render: str | None
    component_differences: dict[str, float]


class GeometryDatasetService:
    """Load calibrated FM head records and compare them with corrected portraits.

    Records must come from a standardised front render or decoded mesh measurements.
    UV textures are not accepted as geometry evidence.
    """

    WEIGHTS = {
        "face_width": 1.35,
        "face_height": 1.20,
        "eye_spacing": 1.10,
        "nose_length": 1.00,
        "mouth_width": 0.90,
        "jaw_width": 1.35,
        "chin_length": 1.10,
        "symmetry": 0.45,
    }

    def load(self, path: Path) -> tuple[HeadGeometryRecord, ...]:
        if not path.is_file():
            raise ValueError(f"Geometry dataset not found: {path}")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Geometry dataset could not be read: {exc}") from exc
        if payload.get("format") != DATASET_FORMAT:
            raise ValueError(f"Expected dataset format {DATASET_FORMAT}.")
        raw_records = payload.get("records")
        if not isinstance(raw_records, list):
            raise ValueError("Geometry dataset must contain a records list.")

        records: list[HeadGeometryRecord] = []
        seen: set[str] = set()
        for index, raw in enumerate(raw_records, start=1):
            if not isinstance(raw, dict):
                raise ValueError(f"Record {index} is not an object.")
            player_id = str(raw.get("player_id", "")).strip()
            if not player_id.isdigit():
                raise ValueError(f"Record {index} has an invalid numeric player_id.")
            if player_id in seen:
                raise ValueError(f"Duplicate player_id in geometry dataset: {player_id}")
            seen.add(player_id)
            source_type = str(raw.get("source_type", "")).strip()
            if source_type not in {"calibrated-render", "decoded-mesh"}:
                raise ValueError(f"Record {player_id} must use calibrated-render or decoded-mesh evidence.")
            confidence = float(raw.get("confidence", 0.0))
            if not 0.0 <= confidence <= 1.0:
                raise ValueError(f"Record {player_id} confidence must be between 0 and 1.")
            values = raw.get("measurements")
            if not isinstance(values, dict):
                raise ValueError(f"Record {player_id} is missing measurements.")
            converted: dict[str, float] = {}
            for name in MEASUREMENT_NAMES:
                try:
                    value = float(values[name])
                except (KeyError, TypeError, ValueError) as exc:
                    raise ValueError(f"Record {player_id} has an invalid {name} value.") from exc
                if name == "symmetry":
                    if not 0.0 <= value <= 1.0:
                        raise ValueError(f"Record {player_id} symmetry must be between 0 and 1.")
                elif not 0.0 < value <= 2.0:
                    raise ValueError(f"Record {player_id} {name} is outside the supported normalised range.")
                converted[name] = value
            records.append(
                HeadGeometryRecord(
                    player_id=player_id,
                    measurements=FaceMeasurements(**converted),
                    source_type=source_type,
                    confidence=confidence,
                    front_render=self._optional_path(raw.get("front_render"), path.parent),
                    side_render=self._optional_path(raw.get("side_render"), path.parent),
                    notes=str(raw.get("notes", "")),
                )
            )
        if not records:
            raise ValueError("Geometry dataset contains no records.")
        return tuple(records)

    def match(
        self,
        portrait: FaceMeasurements,
        records: tuple[HeadGeometryRecord, ...],
        limit: int = 10,
    ) -> tuple[GeometryMatch, ...]:
        if not records:
            raise ValueError("No calibrated geometry records are loaded.")
        total_weight = sum(self.WEIGHTS.values())
        matches: list[GeometryMatch] = []
        for record in records:
            differences = {
                name: abs(getattr(portrait, name) - getattr(record.measurements, name))
                for name in MEASUREMENT_NAMES
            }
            weighted = sum(differences[name] * self.WEIGHTS[name] for name in MEASUREMENT_NAMES) / total_weight
            confidence_penalty = (1.0 - record.confidence) * 0.08
            distance = weighted + confidence_penalty
            score = max(0, min(100, round((1.0 - min(1.0, distance / 0.45)) * 100)))
            matches.append(
                GeometryMatch(
                    player_id=record.player_id,
                    score=score,
                    distance=distance,
                    confidence=record.confidence,
                    source_type=record.source_type,
                    front_render=record.front_render,
                    side_render=record.side_render,
                    component_differences=differences,
                )
            )
        matches.sort(key=lambda item: (item.distance, -item.confidence, item.player_id))
        return tuple(matches[: max(1, limit)])

    @staticmethod
    def save_dataset(records: tuple[HeadGeometryRecord, ...], destination: Path) -> Path:
        destination = destination.with_suffix(".json")
        payload = {
            "format": DATASET_FORMAT,
            "records": [
                {
                    "player_id": record.player_id,
                    "source_type": record.source_type,
                    "confidence": record.confidence,
                    "front_render": record.front_render,
                    "side_render": record.side_render,
                    "notes": record.notes,
                    "measurements": asdict(record.measurements),
                }
                for record in records
            ],
        }
        destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return destination

    @staticmethod
    def _optional_path(value: object, base: Path) -> str | None:
        if value in (None, ""):
            return None
        path = Path(str(value)).expanduser()
        if not path.is_absolute():
            path = (base / path).resolve()
        return str(path)

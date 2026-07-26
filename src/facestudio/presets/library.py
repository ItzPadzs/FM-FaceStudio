from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


@dataclass(slots=True)
class DescriptorPreset:
    id: str
    name: str
    descriptor: dict[str, float | str]
    source_record_id: str = ""
    source_name: str = ""
    confidence: float = 0.0
    collection: str = "Unsorted"
    tags: list[str] = field(default_factory=list)
    favourite: bool = False
    notes: str = ""
    created_at: str = ""

    @classmethod
    def from_dict(cls, payload: dict) -> "DescriptorPreset":
        return cls(
            id=str(payload.get("id") or uuid4()),
            name=str(payload.get("name", "Untitled preset")),
            descriptor=dict(payload.get("descriptor", {})),
            source_record_id=str(payload.get("source_record_id", "")),
            source_name=str(payload.get("source_name", "")),
            confidence=float(payload.get("confidence", 0.0)),
            collection=str(payload.get("collection", "Unsorted")),
            tags=[str(value) for value in payload.get("tags", [])],
            favourite=bool(payload.get("favourite", False)),
            notes=str(payload.get("notes", "")),
            created_at=str(payload.get("created_at", "")),
        )


class DescriptorPresetLibrary:
    def __init__(self, path: Path, history_path: Path) -> None:
        self.path = path
        self.history_path = history_path

    def load(self) -> list[DescriptorPreset]:
        if not self.path.exists():
            return []
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError):
            return []
        return [DescriptorPreset.from_dict(item) for item in payload if isinstance(item, dict)]

    def save(self, presets: list[DescriptorPreset]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(json.dumps([asdict(item) for item in presets], indent=2), encoding="utf-8")
        temporary.replace(self.path)

    def upsert(self, preset: DescriptorPreset) -> None:
        presets = self.load()
        for index, current in enumerate(presets):
            if current.id == preset.id:
                presets[index] = preset
                break
        else:
            presets.insert(0, preset)
        self.save(presets)

    def remove(self, preset_id: str) -> None:
        self.save([item for item in self.load() if item.id != preset_id])

    def import_file(self, path: Path) -> DescriptorPreset:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("format") != "facestudio-descriptor-preset":
            raise ValueError("This file is not a FaceStudio descriptor preset.")
        preset = DescriptorPreset.from_dict(payload.get("preset", {}))
        preset.id = str(uuid4())
        preset.tags = sorted(set(preset.tags + ["imported"]))
        preset.created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        self.upsert(preset)
        return preset

    def export_file(self, preset: DescriptorPreset, path: Path) -> None:
        payload = {"format": "facestudio-descriptor-preset", "schema_version": 1, "preset": asdict(preset)}
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def add_history(self, names: list[str], similarity: float, notes: str = "") -> None:
        history = self.load_history()
        history.insert(0, {
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "presets": names,
            "similarity": round(similarity, 4),
            "notes": notes,
        })
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        self.history_path.write_text(json.dumps(history[:100], indent=2), encoding="utf-8")

    def load_history(self) -> list[dict]:
        if not self.history_path.exists():
            return []
        try:
            payload = json.loads(self.history_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError):
            return []
        return payload if isinstance(payload, list) else []


def descriptor_similarity(first: dict, second: dict) -> tuple[float, dict[str, float]]:
    ranges = {
        "face_height_width_ratio": 0.90,
        "inter_eye_face_width_ratio": 0.30,
        "eye_line_face_height_ratio": 0.35,
        "mouth_line_face_height_ratio": 0.35,
    }
    scores: dict[str, float] = {}
    for key, scale in ranges.items():
        left = float(first.get(key, 0.0))
        right = float(second.get(key, 0.0))
        scores[key] = max(0.0, 1.0 - abs(left - right) / scale)
    scores["face_shape"] = 1.0 if str(first.get("face_shape", "")) == str(second.get("face_shape", "")) else 0.65
    return sum(scores.values()) / len(scores), scores

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


@dataclass(slots=True)
class FaceLibraryRecord:
    id: str
    name: str
    project_path: str
    source_photo: str
    preview_path: str
    analysis_path: str
    face_shape: str
    confidence: float
    measurements: dict[str, float] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    collection: str = "Unsorted"
    notes: str = ""
    favourite: bool = False
    created_at: str = ""

    @classmethod
    def from_dict(cls, payload: dict) -> "FaceLibraryRecord":
        return cls(
            id=str(payload.get("id") or uuid4()),
            name=str(payload.get("name", "Untitled face")),
            project_path=str(payload.get("project_path", "")),
            source_photo=str(payload.get("source_photo", "")),
            preview_path=str(payload.get("preview_path", "")),
            analysis_path=str(payload.get("analysis_path", "")),
            face_shape=str(payload.get("face_shape", "undetermined")),
            confidence=float(payload.get("confidence", 0.0)),
            measurements={str(k): float(v) for k, v in dict(payload.get("measurements", {})).items()},
            tags=[str(value) for value in payload.get("tags", [])],
            collection=str(payload.get("collection", "Unsorted")),
            notes=str(payload.get("notes", "")),
            favourite=bool(payload.get("favourite", False)),
            created_at=str(payload.get("created_at", "")),
        )


class FaceLibraryStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> list[FaceLibraryRecord]:
        if not self.path.exists():
            return []
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError):
            return []
        if not isinstance(payload, list):
            return []
        return [FaceLibraryRecord.from_dict(item) for item in payload if isinstance(item, dict)]

    def save(self, records: list[FaceLibraryRecord]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(json.dumps([asdict(record) for record in records], indent=2), encoding="utf-8")
        temporary.replace(self.path)

    def add_project(self, name: str, project_path: Path, source_photo: str, preview_file: str, analysis_file: str) -> FaceLibraryRecord:
        analysis_path = project_path / analysis_file
        payload = json.loads(analysis_path.read_text(encoding="utf-8"))
        records = self.load()
        existing = next((item for item in records if Path(item.project_path) == project_path), None)
        record = existing or FaceLibraryRecord(
            id=str(uuid4()), name=name, project_path=str(project_path), source_photo="", preview_path="",
            analysis_path="", face_shape="undetermined", confidence=0.0,
            created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )
        record.name = name
        record.source_photo = str(project_path / source_photo) if source_photo else ""
        record.preview_path = str(project_path / preview_file) if preview_file else record.source_photo
        record.analysis_path = str(analysis_path)
        record.face_shape = str(payload.get("face_shape", "undetermined"))
        record.confidence = float(payload.get("confidence", 0.0))
        record.measurements = {str(k): float(v) for k, v in dict(payload.get("measurements", {})).items()}
        if existing is None:
            records.insert(0, record)
        self.save(records)
        return record

    def update(self, record: FaceLibraryRecord) -> None:
        records = self.load()
        for index, current in enumerate(records):
            if current.id == record.id:
                records[index] = record
                break
        self.save(records)

    def remove(self, record_id: str) -> None:
        self.save([item for item in self.load() if item.id != record_id])

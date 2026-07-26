from __future__ import annotations

import importlib.util
import json
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from uuid import uuid4

from facestudio.library.store import FaceLibraryStore
from facestudio.presets.library import DescriptorPresetLibrary, descriptor_similarity


@dataclass(slots=True)
class ResearchProject:
    id: str
    name: str
    description: str = ""
    status: str = "active"
    owner: str = "Local user"
    reviewers: list[str] = field(default_factory=list)
    milestones: list[str] = field(default_factory=list)
    created_at: str = ""

    @classmethod
    def from_dict(cls, payload: dict) -> "ResearchProject":
        return cls(
            id=str(payload.get("id") or uuid4()),
            name=str(payload.get("name", "Untitled project")),
            description=str(payload.get("description", "")),
            status=str(payload.get("status", "active")),
            owner=str(payload.get("owner", "Local user")),
            reviewers=[str(value) for value in payload.get("reviewers", [])],
            milestones=[str(value) for value in payload.get("milestones", [])],
            created_at=str(payload.get("created_at", "")),
        )


class PlatformService:
    """Local, transparent platform tools built on FaceStudio metadata."""

    def __init__(
        self,
        data_dir: Path,
        face_store: FaceLibraryStore,
        preset_store: DescriptorPresetLibrary,
    ) -> None:
        self.data_dir = data_dir
        self.face_store = face_store
        self.preset_store = preset_store
        self.projects_path = data_dir / "research-projects.json"
        self.plugins_dir = data_dir / "plugins"
        self.plugins_dir.mkdir(parents=True, exist_ok=True)

    def assistant_summary(self) -> list[str]:
        faces = self.face_store.load()
        presets = self.preset_store.load()
        messages: list[str] = []
        low_confidence = [item for item in faces if item.confidence < 0.55]
        if low_confidence:
            messages.append(f"{len(low_confidence)} face analyses are below 55% confidence and may benefit from review.")
        shapes = Counter(item.face_shape for item in faces if item.face_shape)
        if shapes:
            shape, count = shapes.most_common(1)[0]
            messages.append(f"The most common face shape is {shape}, appearing in {count} library records.")
        if len(presets) >= 2:
            best: tuple[float, str, str] | None = None
            for index, first in enumerate(presets):
                for second in presets[index + 1:]:
                    score, _ = descriptor_similarity(first.descriptor, second.descriptor)
                    if best is None or score > best[0]:
                        best = (score, first.name, second.name)
            if best is not None:
                messages.append(f"The closest preset pair is {best[1]} and {best[2]} at {best[0] * 100:.1f}% descriptor similarity.")
        if not messages:
            messages.append("Add analysed faces or descriptor presets to receive local research guidance.")
        return messages

    def visualisation_data(self) -> dict:
        faces = self.face_store.load()
        presets = self.preset_store.load()
        return {
            "face_shapes": dict(Counter(item.face_shape for item in faces)),
            "collections": dict(Counter(item.collection for item in faces + presets)),
            "confidence_bands": {
                "high": sum(item.confidence >= 0.8 for item in faces),
                "medium": sum(0.55 <= item.confidence < 0.8 for item in faces),
                "low": sum(item.confidence < 0.55 for item in faces),
            },
            "average_confidence": mean([item.confidence for item in faces]) if faces else 0.0,
        }

    def discover_plugins(self) -> list[dict]:
        plugins: list[dict] = []
        for manifest in sorted(self.plugins_dir.glob("*/facestudio-plugin.json")):
            try:
                payload = json.loads(manifest.read_text(encoding="utf-8"))
            except (OSError, ValueError, json.JSONDecodeError):
                plugins.append({"name": manifest.parent.name, "status": "invalid manifest"})
                continue
            module_name = str(payload.get("module", ""))
            module_path = manifest.parent / module_name if module_name else None
            status = "ready" if module_path and module_path.exists() else "missing module"
            plugins.append({
                "name": str(payload.get("name", manifest.parent.name)),
                "version": str(payload.get("version", "unknown")),
                "type": str(payload.get("type", "tool")),
                "status": status,
            })
        return plugins

    def validate_plugin(self, plugin_dir: Path) -> tuple[bool, str]:
        manifest = plugin_dir / "facestudio-plugin.json"
        if not manifest.exists():
            return False, "Missing facestudio-plugin.json."
        try:
            payload = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            return False, f"Invalid manifest: {exc}"
        module_name = str(payload.get("module", ""))
        if not payload.get("name") or not module_name:
            return False, "Plugin name and module are required."
        module_path = plugin_dir / module_name
        if not module_path.exists():
            return False, f"Plugin module {module_name} is missing."
        spec = importlib.util.spec_from_file_location("facestudio_external_plugin", module_path)
        if spec is None:
            return False, "Plugin module could not be inspected."
        return True, "Plugin manifest and module are available. Plugins are not executed during validation."

    def load_projects(self) -> list[ResearchProject]:
        if not self.projects_path.exists():
            return []
        try:
            payload = json.loads(self.projects_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError):
            return []
        return [ResearchProject.from_dict(item) for item in payload if isinstance(item, dict)]

    def save_projects(self, projects: list[ResearchProject]) -> None:
        self.projects_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.projects_path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps([asdict(item) for item in projects], indent=2), encoding="utf-8")
        temporary.replace(self.projects_path)

    def add_project(self, name: str, description: str = "") -> ResearchProject:
        projects = self.load_projects()
        project = ResearchProject(
            id=str(uuid4()),
            name=name.strip() or "Untitled project",
            description=description.strip(),
            created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )
        projects.insert(0, project)
        self.save_projects(projects)
        return project

    def module_registry(self) -> list[dict[str, str]]:
        return [
            {"module": "Project Workspace", "status": "available"},
            {"module": "Asset Explorer", "status": "available"},
            {"module": "Face Analysis", "status": "available"},
            {"module": "Batch Analysis", "status": "available"},
            {"module": "Face Library", "status": "available"},
            {"module": "Descriptor Presets", "status": "available"},
            {"module": "Research Suite", "status": "available"},
            {"module": "Research Assistant", "status": "available"},
            {"module": "Visualisation", "status": "available"},
            {"module": "Plugin SDK", "status": "preview"},
            {"module": "Team Projects", "status": "local metadata"},
        ]

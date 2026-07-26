from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class RecentProject:
    name: str
    path: str


class RecentProjectsStore:
    def __init__(self, path: Path, limit: int = 10) -> None:
        self.path = path
        self.limit = max(1, limit)

    def load(self) -> list[RecentProject]:
        if not self.path.exists():
            return []

        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError):
            return []

        projects: list[RecentProject] = []
        if not isinstance(payload, list):
            return projects

        for item in payload:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "")).strip()
            project_path = str(item.get("path", "")).strip()
            if name and project_path:
                projects.append(RecentProject(name=name, path=project_path))

        return projects[: self.limit]

    def add(self, project: RecentProject) -> None:
        items = [
            item
            for item in self.load()
            if Path(item.path) != Path(project.path)
        ]
        items.insert(0, project)
        self.save(items[: self.limit])

    def remove_missing(self) -> list[RecentProject]:
        items = [
            item
            for item in self.load()
            if Path(item.path).exists()
        ]
        self.save(items)
        return items

    def save(self, items: list[RecentProject]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        payload = [
            {"name": item.name, "path": item.path}
            for item in items[: self.limit]
        ]
        temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        temporary.replace(self.path)

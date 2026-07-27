from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
import os
from pathlib import Path
from typing import Iterable

INDEX_FORMAT = "facestudio-library-index-v1"


@dataclass
class LibraryIndex:
    roots: list[str] = field(default_factory=list)
    geometry_dataset: str = ""
    donor_assets_directory: str = ""
    uv_profiles_directory: str = ""
    projects_directory: str = ""
    geometry_records: int = 0
    donor_textures: int = 0
    uv_profiles: int = 0
    projects: int = 0
    warnings: list[str] = field(default_factory=list)

    def save(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = asdict(self); payload["format"] = INDEX_FORMAT
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return path

    @classmethod
    def load(cls, path: Path) -> "LibraryIndex":
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.pop("format", None) != INDEX_FORMAT:
            raise ValueError(f"Expected {INDEX_FORMAT}.")
        return cls(**payload)


class LibraryDiscoveryService:
    """Discover FaceStudio and Football Manager resources without assigning false meaning."""

    def discover(self, saved_roots: Iterable[Path] = ()) -> LibraryIndex:
        roots = self._roots(saved_roots)
        datasets: list[tuple[Path, int]] = []
        textures: list[Path] = []
        profiles: list[Path] = []
        projects: list[Path] = []
        warnings: list[str] = []

        for root in roots:
            if not root.is_dir():
                continue
            try:
                for path in root.rglob("*"):
                    if not path.is_file():
                        continue
                    suffix = path.suffix.lower()
                    if suffix == ".json":
                        kind, count = self._classify_json(path)
                        if kind == "geometry": datasets.append((path, count))
                        elif kind == "uv": profiles.append(path)
                        elif kind == "project": projects.append(path)
                    elif suffix == ".png" and path.stem.isdigit():
                        textures.append(path)
            except (OSError, PermissionError) as exc:
                warnings.append(f"Could not fully scan {root}: {exc}")

        dataset = max(datasets, key=lambda item: (item[1], str(item[0])), default=(Path(), 0))
        assets_dir = self._common_parent(textures)
        profile_dir = self._common_parent(profiles)
        project_dir = self._common_parent(projects)
        if not datasets: warnings.append("No calibrated geometry dataset was discovered.")
        if not textures: warnings.append("No numeric donor PNG textures were discovered.")

        return LibraryIndex(
            roots=[str(path) for path in roots],
            geometry_dataset=str(dataset[0]) if dataset[0] else "",
            donor_assets_directory=str(assets_dir) if assets_dir else "",
            uv_profiles_directory=str(profile_dir) if profile_dir else "",
            projects_directory=str(project_dir) if project_dir else "",
            geometry_records=dataset[1], donor_textures=len(textures),
            uv_profiles=len(profiles), projects=len(projects), warnings=warnings,
        )

    @staticmethod
    def _classify_json(path: Path) -> tuple[str, int]:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            return "", 0
        fmt = payload.get("format")
        if fmt == "facestudio-fm-head-geometry-v1":
            records = payload.get("records", [])
            return "geometry", len(records) if isinstance(records, list) else 0
        if fmt == "facestudio-donor-uv-calibration-v1": return "uv", 1
        if fmt in {"facestudio-builder-workspace-v1", "facestudio-automatic-build-v2"}: return "project", 1
        return "", 0

    @staticmethod
    def _common_parent(paths: list[Path]) -> Path | None:
        if not paths: return None
        try: return Path(os.path.commonpath([str(path.parent) for path in paths]))
        except ValueError: return paths[0].parent

    @staticmethod
    def _roots(saved_roots: Iterable[Path]) -> list[Path]:
        candidates = list(saved_roots)
        home = Path.home()
        candidates.extend([
            home / "Documents" / "Sports Interactive",
            home / "Documents",
            home / "FM FaceStudio",
            home / "AppData" / "Local" / "Sports Interactive",
            Path(os.environ.get("PROGRAMFILES", "C:/Program Files")) / "Steam" / "steamapps" / "common",
            Path(os.environ.get("PROGRAMFILES(X86)", "C:/Program Files (x86)")) / "Steam" / "steamapps" / "common",
        ])
        seen: set[str] = set(); result: list[Path] = []
        for path in candidates:
            resolved = Path(path).expanduser()
            key = str(resolved).lower()
            if key not in seen and resolved.exists(): seen.add(key); result.append(resolved)
        return result

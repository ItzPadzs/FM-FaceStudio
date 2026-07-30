from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path

PROJECT_FORMAT = "facestudio-project-v1"


@dataclass
class FaceStudioProject:
    name: str
    directory: Path
    portrait: Path | None = None
    donor_texture: Path | None = None
    generated_texture: Path | None = None
    mask_profile: str = "fm-default-v1"
    colour_strength: float = 0.85
    diagnostics: list[Path] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def manifest_path(self) -> Path:
        return self.directory / "project.json"

    @property
    def output_directory(self) -> Path:
        return self.directory / "output"

    @property
    def diagnostics_directory(self) -> Path:
        return self.directory / "diagnostics"

    def validate(self) -> None:
        if not self.name.strip():
            raise ValueError("Project name cannot be empty")
        if not 0.0 <= self.colour_strength <= 1.0:
            raise ValueError("Colour strength must be between 0 and 1")

    def save(self) -> Path:
        self.validate()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.output_directory.mkdir(exist_ok=True)
        self.diagnostics_directory.mkdir(exist_ok=True)
        self.updated_at = datetime.now(timezone.utc).isoformat()
        payload = asdict(self)
        payload["format"] = PROJECT_FORMAT
        payload["directory"] = str(self.directory)
        for key in ("portrait", "donor_texture", "generated_texture"):
            payload[key] = str(payload[key]) if payload[key] else None
        payload["diagnostics"] = [str(path) for path in self.diagnostics]
        self.manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return self.manifest_path

    @classmethod
    def load(cls, manifest: Path) -> "FaceStudioProject":
        manifest = Path(manifest).expanduser().resolve()
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        if payload.get("format") != PROJECT_FORMAT:
            raise ValueError("Unsupported FaceStudio project format")
        project = cls(
            name=str(payload["name"]),
            directory=Path(payload.get("directory") or manifest.parent),
            portrait=Path(payload["portrait"]) if payload.get("portrait") else None,
            donor_texture=Path(payload["donor_texture"]) if payload.get("donor_texture") else None,
            generated_texture=Path(payload["generated_texture"]) if payload.get("generated_texture") else None,
            mask_profile=str(payload.get("mask_profile", "fm-default-v1")),
            colour_strength=float(payload.get("colour_strength", 0.85)),
            diagnostics=[Path(value) for value in payload.get("diagnostics", [])],
            created_at=str(payload.get("created_at", "")),
            updated_at=str(payload.get("updated_at", "")),
        )
        project.validate()
        return project

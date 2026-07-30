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
    aligned_portrait: Path | None = None
    alignment_landmarks: dict[str, list[float]] = field(default_factory=dict)
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

    @property
    def alignment_directory(self) -> Path:
        return self.directory / "alignment"

    def validate(self) -> None:
        if not self.name.strip():
            raise ValueError("Project name cannot be empty")
        if not 0.0 <= self.colour_strength <= 1.0:
            raise ValueError("Colour strength must be between 0 and 1")
        expected = {"left_eye", "right_eye", "nose_tip", "mouth_centre", "chin"}
        if self.alignment_landmarks and set(self.alignment_landmarks) != expected:
            raise ValueError("Alignment landmarks must contain the five canonical point names")
        for point in self.alignment_landmarks.values():
            if len(point) != 2 or any(float(value) < 0.0 or float(value) > 1.0 for value in point):
                raise ValueError("Alignment landmarks must use normalised x/y coordinates")

    def save(self) -> Path:
        self.validate()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.output_directory.mkdir(exist_ok=True)
        self.diagnostics_directory.mkdir(exist_ok=True)
        self.alignment_directory.mkdir(exist_ok=True)
        self.updated_at = datetime.now(timezone.utc).isoformat()
        payload = asdict(self)
        payload["format"] = PROJECT_FORMAT
        payload["directory"] = str(self.directory)
        for key in ("portrait", "aligned_portrait", "donor_texture", "generated_texture"):
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
            aligned_portrait=Path(payload["aligned_portrait"]) if payload.get("aligned_portrait") else None,
            alignment_landmarks={
                str(key): [float(value[0]), float(value[1])]
                for key, value in payload.get("alignment_landmarks", {}).items()
            },
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

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
from typing import Callable, Protocol

from PySide6.QtGui import QImage, QImageReader

GENERATION_RECORD_FORMAT = "facestudio-generation-record-v1"
ProgressCallback = Callable[[int, str, Path | None], None]


@dataclass(frozen=True)
class GenerationSettings:
    engine: str = "donor-baseline"
    preserve_hair: bool = True
    preserve_beard: bool = True
    strength: float = 1.0

    def validate(self) -> None:
        if not 0.0 <= self.strength <= 1.0:
            raise ValueError("Generation strength must be between 0 and 1")


@dataclass(frozen=True)
class GenerationRequest:
    portrait: Path
    donor_texture: Path
    output: Path
    donor_id: str | None = None
    donor_name: str | None = None
    settings: GenerationSettings = field(default_factory=GenerationSettings)

    def validate(self) -> None:
        self.settings.validate()
        if not Path(self.portrait).is_file():
            raise ValueError(f"Portrait not found: {self.portrait}")
        if not Path(self.donor_texture).is_file():
            raise ValueError(f"Donor texture not found: {self.donor_texture}")
        if Path(self.output).suffix.lower() != ".png":
            raise ValueError("Generated FM textures must be written as PNG files")


@dataclass(frozen=True)
class GenerationResult:
    output: Path
    engine: str
    donor_id: str | None
    donor_name: str | None
    stages: tuple[str, ...]
    metadata: dict[str, object] = field(default_factory=dict)


class IdentityTransferEngine(Protocol):
    """Stable generation boundary used by the desktop application.

    Implementations may be deterministic, ONNX-based, Torch-based or remote, but they
    must accept the same request and return a complete FM UV texture plus provenance.
    """

    name: str

    @property
    def available(self) -> bool: ...

    @property
    def status_message(self) -> str: ...

    def generate(
        self,
        request: GenerationRequest,
        progress: ProgressCallback | None = None,
    ) -> GenerationResult: ...


class DonorBaselineEngine:
    """Safe baseline engine that preserves the selected donor texture unchanged.

    This is intentionally not described as identity transfer. It proves the common engine
    contract, progressive events, export path and provenance capture until trained model
    weights or a reviewed regional composer are connected.
    """

    name = "donor-baseline"

    @property
    def available(self) -> bool:
        return True

    @property
    def status_message(self) -> str:
        return "Donor baseline engine is ready; no portrait identity is transferred."

    def generate(
        self,
        request: GenerationRequest,
        progress: ProgressCallback | None = None,
    ) -> GenerationResult:
        request.validate()
        stages: list[str] = []

        def emit(percent: int, message: str, preview: Path | None = None) -> None:
            stages.append(message)
            if progress is not None:
                progress(percent, message, preview)

        emit(5, "Validating portrait and donor")
        self._read_image(request.portrait)
        donor = self._read_image(request.donor_texture)
        emit(30, "Loading selected donor UV", request.donor_texture)
        emit(55, "Preparing generation request")

        output = Path(request.output).expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        if not donor.save(str(output), "PNG"):
            raise RuntimeError(f"Could not write generated texture: {output}")

        emit(90, "Writing FM UV texture", output)
        emit(100, "Generation complete", output)
        return GenerationResult(
            output=output,
            engine=self.name,
            donor_id=request.donor_id,
            donor_name=request.donor_name,
            stages=tuple(stages),
            metadata={
                "identity_transfer": False,
                "portrait_used_for_pixels": False,
                "accuracy_boundary": "Selected donor copied unchanged by baseline engine",
            },
        )

    @staticmethod
    def _read_image(path: Path) -> QImage:
        reader = QImageReader(str(path))
        reader.setAutoTransform(True)
        image = reader.read()
        if image.isNull():
            raise ValueError(f"Could not read image {path}: {reader.errorString()}")
        return image


class EngineRegistry:
    def __init__(self, engines: list[IdentityTransferEngine] | None = None) -> None:
        self._engines: dict[str, IdentityTransferEngine] = {}
        for engine in engines or [DonorBaselineEngine()]:
            self.register(engine)

    def register(self, engine: IdentityTransferEngine) -> None:
        if not engine.name:
            raise ValueError("Generation engines require a non-empty name")
        self._engines[engine.name] = engine

    def get(self, name: str) -> IdentityTransferEngine:
        try:
            return self._engines[name]
        except KeyError as exc:
            available = ", ".join(sorted(self._engines)) or "none"
            raise ValueError(f"Unknown generation engine '{name}'. Available: {available}") from exc

    def available(self) -> tuple[str, ...]:
        return tuple(sorted(name for name, engine in self._engines.items() if engine.available))

    def generate(
        self,
        request: GenerationRequest,
        progress: ProgressCallback | None = None,
    ) -> GenerationResult:
        engine = self.get(request.settings.engine)
        if not engine.available:
            raise RuntimeError(engine.status_message)
        return engine.generate(request, progress)


class TrainingCapture:
    """Store reviewed generation provenance without silently collecting user images."""

    def capture(
        self,
        directory: Path,
        request: GenerationRequest,
        result: GenerationResult,
        *,
        approved: bool,
        final_texture: Path | None = None,
        notes: str = "",
        copy_assets: bool = False,
    ) -> Path:
        directory = Path(directory).expanduser().resolve()
        directory.mkdir(parents=True, exist_ok=True)
        final = Path(final_texture or result.output).expanduser().resolve()
        if not final.is_file():
            raise ValueError(f"Reviewed final texture not found: {final}")

        asset_paths = {
            "portrait": Path(request.portrait).expanduser().resolve(),
            "donor_texture": Path(request.donor_texture).expanduser().resolve(),
            "generated_texture": Path(result.output).expanduser().resolve(),
            "final_texture": final,
        }
        if copy_assets:
            assets = directory / "assets"
            assets.mkdir(exist_ok=True)
            copied: dict[str, Path] = {}
            for label, source in asset_paths.items():
                target = assets / f"{label}{source.suffix.lower()}"
                shutil.copy2(source, target)
                copied[label] = target
            asset_paths = copied

        payload = {
            "format": GENERATION_RECORD_FORMAT,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "approved": bool(approved),
            "notes": notes,
            "request": {
                "portrait": str(asset_paths["portrait"]),
                "donor_texture": str(asset_paths["donor_texture"]),
                "donor_id": request.donor_id,
                "donor_name": request.donor_name,
                "settings": asdict(request.settings),
            },
            "result": {
                "generated_texture": str(asset_paths["generated_texture"]),
                "final_texture": str(asset_paths["final_texture"]),
                "engine": result.engine,
                "stages": list(result.stages),
                "metadata": result.metadata,
            },
        }
        record = directory / "generation-record.json"
        record.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return record

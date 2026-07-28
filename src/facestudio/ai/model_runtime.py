from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Callable

MODEL_MANIFEST_FORMAT = "facestudio-portrait-to-uv-model-v1"
ProgressCallback = Callable[[int, str, Path | None], None]


@dataclass(frozen=True)
class ModelManifest:
    format: str
    model_name: str
    version: str
    weights: str
    input_size: int
    output_size: int
    backend: str


class PortraitToUVModel:
    """Runtime boundary for a future trained portrait-to-FM UV model.

    Alpha 12 deliberately refuses to pretend that template compositing is an AI model.
    Generation is enabled only when a validated model manifest and weights exist.
    """

    def __init__(self, model_directory: Path) -> None:
        self.model_directory = Path(model_directory).expanduser().resolve()
        self.manifest_path = self.model_directory / "model.json"
        self.manifest = self._load_manifest()

    @property
    def available(self) -> bool:
        if self.manifest is None:
            return False
        return (self.model_directory / self.manifest.weights).is_file()

    @property
    def status_message(self) -> str:
        if self.manifest is None:
            return "No trained portrait-to-UV model is installed."
        if not self.available:
            return f"Model weights are missing: {self.manifest.weights}"
        return f"{self.manifest.model_name} {self.manifest.version} is ready."

    def generate(self, portrait: Path, output: Path, progress: ProgressCallback | None = None) -> Path:
        if not self.available:
            raise RuntimeError(
                "A trained portrait-to-FM UV model has not been installed. "
                "Build a paired dataset, train/export the model, then place model.json "
                "and its declared weights in the configured model folder."
            )
        # The stable contract is in place, but an inference backend is intentionally not
        # fabricated. ONNX or Torch execution is added when real exported weights exist.
        raise NotImplementedError(
            f"The '{self.manifest.backend}' inference adapter is not implemented yet."
        )

    def _load_manifest(self) -> ModelManifest | None:
        if not self.manifest_path.is_file():
            return None
        payload = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        required = {"format", "model_name", "version", "weights", "input_size", "output_size", "backend"}
        missing = required - payload.keys()
        if missing:
            raise ValueError(f"Model manifest is missing: {', '.join(sorted(missing))}")
        if payload["format"] != MODEL_MANIFEST_FORMAT:
            raise ValueError(f"Unsupported model manifest format: {payload['format']}")
        return ModelManifest(**{key: payload[key] for key in required})

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from facestudio.ai.fm_style_renderer import FMStyleRendererEngine
from facestudio.ai.generation_engine import EngineRegistry, GenerationRequest, GenerationResult, GenerationSettings
from facestudio.ai.trained_portrait_uv import TrainedPortraitUVEngine
from facestudio.donor_asset_index import DonorMatch, DonorMatcher


@dataclass(frozen=True)
class FaceStudio2Result:
    donor: DonorMatch
    generation: GenerationResult


class FaceStudio2Pipeline:
    """Use trained portrait-to-UV inference when weights are installed; retain an explicit prototype fallback."""

    def __init__(self, donor_index: Path, model_dir: Path | None = None) -> None:
        self.matcher = DonorMatcher(donor_index)
        default_model_dir = Path(donor_index).resolve().parent.parent / "models" / "portrait-uv"
        self.model_dir = Path(model_dir or os.environ.get("FACESTUDIO_MODEL_DIR", default_model_dir))
        self.registry = EngineRegistry()
        self.trained = TrainedPortraitUVEngine(self.model_dir)
        if self.trained.available:
            self.registry.register(self.trained)
            self.engine_name = self.trained.name
            self.engine_status = "Trained portrait-to-UV model ACTIVE"
        else:
            self.registry.register(FMStyleRendererEngine())
            self.engine_name = "fm-style-renderer-v1"
            self.engine_status = "PROTOTYPE fallback active — trained model not installed"

    def run(self, portrait: Path, output: Path, progress=None) -> FaceStudio2Result:
        matches = self.matcher.rank(portrait, limit=1)
        if not matches:
            raise RuntimeError("The donor index contains no usable diffuse textures")
        donor = matches[0]
        if progress:
            prefix = "Trained model input prepared" if self.trained.available else "Prototype donor prior selected"
            progress(2, f"{prefix}: {donor.name} ({donor.score:.2f}%)", Path(donor.face_crop) if donor.face_crop else None)
        request = GenerationRequest(
            portrait=Path(portrait), donor_texture=Path(donor.diffuse), output=Path(output),
            donor_id=donor.donor_id, donor_name=donor.name,
            settings=GenerationSettings(engine=self.engine_name, strength=1.0),
        )
        return FaceStudio2Result(donor=donor, generation=self.registry.generate(request, progress))

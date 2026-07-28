from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from facestudio.ai.fm_style_renderer import FMStyleRendererEngine
from facestudio.ai.generation_engine import EngineRegistry, GenerationRequest, GenerationResult, GenerationSettings
from facestudio.donor_asset_index import DonorMatch, DonorMatcher


@dataclass(frozen=True)
class FaceStudio2Result:
    donor: DonorMatch
    generation: GenerationResult


class FaceStudio2Pipeline:
    """Portrait -> fixed UV geometry -> deterministic FM diffuse-style texture."""

    def __init__(self, donor_index: Path) -> None:
        self.matcher = DonorMatcher(donor_index)
        self.registry = EngineRegistry()
        self.registry.register(FMStyleRendererEngine())

    def run(self, portrait: Path, output: Path, progress=None) -> FaceStudio2Result:
        matches = self.matcher.rank(portrait, limit=1)
        if not matches:
            raise RuntimeError("The donor index contains no usable diffuse textures")
        donor = matches[0]
        if progress:
            progress(2, f"Selected fixed-UV donor prior: {donor.name} ({donor.score:.2f}%)", Path(donor.face_crop) if donor.face_crop else None)
        request = GenerationRequest(
            portrait=Path(portrait),
            donor_texture=Path(donor.diffuse),
            output=Path(output),
            donor_id=donor.donor_id,
            donor_name=donor.name,
            settings=GenerationSettings(engine="fm-style-renderer-v1", strength=1.0),
        )
        return FaceStudio2Result(donor=donor, generation=self.registry.generate(request, progress))

from __future__ import annotations

from pathlib import Path

from facestudio.ai.generation_engine import (
    GenerationRequest,
    GenerationResult,
    ProgressCallback,
)
from facestudio.ai.model_runtime import PortraitToUVModel


class PortraitToUVModelEngine:
    """Adapt an installed portrait-to-UV model to the common generation contract."""

    name = "portrait-to-uv-model"

    def __init__(self, model_directory: Path) -> None:
        self.model = PortraitToUVModel(model_directory)

    @property
    def available(self) -> bool:
        return self.model.available

    @property
    def status_message(self) -> str:
        return self.model.status_message

    def generate(
        self,
        request: GenerationRequest,
        progress: ProgressCallback | None = None,
    ) -> GenerationResult:
        request.validate()
        output = self.model.generate(request.portrait, request.output, progress)
        return GenerationResult(
            output=output,
            engine=self.name,
            donor_id=request.donor_id,
            donor_name=request.donor_name,
            stages=("Portrait-to-UV model generation complete",),
            metadata={
                "identity_transfer": True,
                "model_directory": str(self.model.model_directory),
                "donor_supplied_as_prior": bool(request.donor_id),
            },
        )

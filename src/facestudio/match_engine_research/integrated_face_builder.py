from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from facestudio.match_engine_research.texture_reconstruction import TextureReconstructionService
from facestudio.match_engine_research.texture_refinement import RefinementSettings, TextureRefinementService
from facestudio.match_engine_research.texture_validation import TextureValidationService, ValidationResult

PROJECT_FORMAT = "facestudio-integrated-build-v1"


@dataclass(frozen=True)
class IntegratedBuildInputs:
    portrait_record: Path
    donor_uv_record: Path
    workspace: Path
    transfer_strength: float = 0.92
    feather_radius: int = 6
    colour_matching: float = 0.65
    neighbour_blend: float = 0.35


@dataclass(frozen=True)
class IntegratedBuildResult:
    player_id: str
    reconstruction_manifest: Path
    refinement_manifest: Path
    validation_result: ValidationResult
    package_directory: Path | None
    project_manifest: Path


class IntegratedFaceBuilderService:
    """Run the reviewed texture pipeline as one traceable operation.

    The portrait landmarks and donor UV anchors remain reviewed prerequisites.
    This service integrates reconstruction, refinement, validation and optional
    reversible packaging; it does not infer FM mesh geometry or edit game files.
    """

    def build(self, inputs: IntegratedBuildInputs, create_package: bool = True) -> IntegratedBuildResult:
        workspace = Path(inputs.workspace).expanduser().resolve()
        workspace.mkdir(parents=True, exist_ok=True)
        reconstruction = TextureReconstructionService().reconstruct(
            Path(inputs.portrait_record),
            Path(inputs.donor_uv_record),
            inputs.transfer_strength,
        )
        _, reconstruction_manifest = TextureReconstructionService.save(
            reconstruction, workspace / f"{reconstruction.player_id}-reconstructed"
        )

        refined = TextureRefinementService().refine(
            reconstruction_manifest,
            RefinementSettings(
                inputs.feather_radius,
                inputs.colour_matching,
                inputs.neighbour_blend,
            ),
        )
        _, refinement_manifest = TextureRefinementService.save(
            refined, workspace / f"{reconstruction.player_id}-refined"
        )

        validation = TextureValidationService().validate(refinement_manifest)
        TextureValidationService.save_report(
            validation, workspace / f"{reconstruction.player_id}-validation"
        )
        package = None
        if create_package and validation.ready_for_testing:
            package = TextureValidationService.create_test_package(validation, workspace)

        project_manifest = workspace / "facestudio-integrated-build.json"
        project_manifest.write_text(json.dumps({
            "format": PROJECT_FORMAT,
            "player_id": reconstruction.player_id,
            "portrait_record": str(Path(inputs.portrait_record)),
            "donor_uv_record": str(Path(inputs.donor_uv_record)),
            "reconstruction_manifest": str(reconstruction_manifest),
            "refinement_manifest": str(refinement_manifest),
            "validation_score": validation.quality_score,
            "ready_for_controlled_testing": validation.ready_for_testing,
            "test_package": str(package) if package else None,
            "settings": {
                "transfer_strength": max(0.0, min(1.0, inputs.transfer_strength)),
                "feather_radius": max(0, min(20, inputs.feather_radius)),
                "colour_matching": max(0.0, min(1.0, inputs.colour_matching)),
                "neighbour_blend": max(0.0, min(1.0, inputs.neighbour_blend)),
            },
            "accuracy_boundary": "Texture integration for an existing reviewed donor head; no .skin, rigging, mesh reconstruction or automatic FM installation.",
        }, indent=2), encoding="utf-8")
        return IntegratedBuildResult(
            reconstruction.player_id,
            reconstruction_manifest,
            refinement_manifest,
            validation,
            package,
            project_manifest,
        )

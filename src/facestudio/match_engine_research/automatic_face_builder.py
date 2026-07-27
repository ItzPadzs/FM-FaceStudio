from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from facestudio.match_engine_research.automatic_calibration import AutomaticCalibrationService
from facestudio.match_engine_research.geometry_dataset import GeometryDatasetService, GeometryMatch
from facestudio.match_engine_research.integrated_face_builder import (
    IntegratedBuildInputs,
    IntegratedBuildResult,
    IntegratedFaceBuilderService,
)

AUTO_BUILD_FORMAT = "facestudio-automatic-build-v2"


@dataclass(frozen=True)
class AutomaticBuildInputs:
    photo: Path
    geometry_dataset: Path
    donor_assets_directory: Path
    workspace: Path
    uv_profiles_directory: Path | None = None


@dataclass(frozen=True)
class AutomaticBuildResult:
    selected_match: GeometryMatch
    portrait_record: Path
    geometry_record: Path
    uv_record: Path
    integrated: IntegratedBuildResult
    automatic_manifest: Path
    warnings: tuple[str, ...]
    generated_uv_profile: bool


class AutomaticFaceBuilderService:
    """Photo-first build with provisional automatic calibration and editable records."""

    def build(self, inputs: AutomaticBuildInputs) -> AutomaticBuildResult:
        photo = Path(inputs.photo).expanduser().resolve()
        dataset_path = Path(inputs.geometry_dataset).expanduser().resolve()
        assets = Path(inputs.donor_assets_directory).expanduser().resolve()
        workspace = Path(inputs.workspace).expanduser().resolve()
        profiles = Path(inputs.uv_profiles_directory or workspace / "uv-profiles").expanduser().resolve()
        if not photo.is_file():
            raise ValueError(f"Photograph not found: {photo}")
        if not assets.is_dir():
            raise ValueError(f"Donor asset folder not found: {assets}")
        workspace.mkdir(parents=True, exist_ok=True)
        profiles.mkdir(parents=True, exist_ok=True)

        calibration = AutomaticCalibrationService()
        analysis, portrait_record, geometry_record = calibration.calibrate_geometry(photo, workspace)

        geometry = GeometryDatasetService()
        records = geometry.load(dataset_path)
        matches = geometry.match(analysis.measurements, records, limit=max(10, len(records)))
        selected: GeometryMatch | None = None
        uv_record: Path | None = None
        generated = False
        for match in matches:
            existing = self._find_uv_profile(profiles, match.player_id)
            if existing is not None:
                selected, uv_record = match, existing
                break
            texture = calibration.find_donor_texture(assets, match.player_id)
            if texture is not None:
                selected = match
                uv_record = calibration.create_uv_profile(match.player_id, texture, profiles)
                generated = True
                break
        if selected is None or uv_record is None:
            raise ValueError(
                "No geometry-matched donor texture could be found. Add numeric donor PNGs to the configured donor asset folder."
            )

        integrated = IntegratedFaceBuilderService().build(
            IntegratedBuildInputs(portrait_record, uv_record, workspace)
        )
        warnings = tuple(analysis.warnings) + (
            "Portrait geometry was generated as a provisional automatic estimate and can be fine-tuned.",
            "The donor UV profile was automatically estimated and can be fine-tuned." if generated else "A saved donor UV profile was reused.",
            "Automatic readiness is advisory; inspect the preview before any controlled FM test.",
        )
        manifest = workspace / "facestudio-automatic-build.json"
        manifest.write_text(json.dumps({
            "format": AUTO_BUILD_FORMAT,
            "photo": str(photo),
            "portrait_record": str(portrait_record),
            "geometry_calibration": str(geometry_record),
            "geometry_dataset": str(dataset_path),
            "donor_assets_directory": str(assets),
            "selected_donor": selected.player_id,
            "geometry_score": selected.score,
            "geometry_distance": selected.distance,
            "uv_profile": str(uv_record),
            "uv_profile_generated": generated,
            "integrated_manifest": str(integrated.project_manifest),
            "validation_score": integrated.validation_result.quality_score,
            "ready_for_controlled_testing": integrated.validation_result.ready_for_testing,
            "fine_tuning": {
                "geometry_record": str(geometry_record),
                "uv_record": str(uv_record),
                "rebuild_required_after_changes": True,
            },
            "warnings": list(warnings),
            "accuracy_boundary": "Provisional editable 2D geometry and UV estimates for an existing donor; no mesh or .skin generation.",
        }, indent=2), encoding="utf-8")
        return AutomaticBuildResult(selected, portrait_record, geometry_record, uv_record, integrated, manifest, warnings, generated)

    @staticmethod
    def _find_uv_profile(root: Path, player_id: str) -> Path | None:
        for path in sorted(root.rglob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if (
                payload.get("format") == "facestudio-donor-uv-calibration-v1"
                and str(payload.get("player_id", "")) == player_id
                and payload.get("complete") is True
            ):
                return path
        return None

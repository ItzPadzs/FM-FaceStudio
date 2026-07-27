from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from facestudio.match_engine_research.geometry_dataset import GeometryDatasetService, GeometryMatch
from facestudio.match_engine_research.integrated_face_builder import (
    IntegratedBuildInputs,
    IntegratedBuildResult,
    IntegratedFaceBuilderService,
)
from facestudio.match_engine_research.one_click_face_builder import OneClickFaceBuilder

AUTO_BUILD_FORMAT = "facestudio-automatic-build-v1"


@dataclass(frozen=True)
class AutomaticBuildInputs:
    photo: Path
    geometry_dataset: Path
    uv_profiles_directory: Path
    workspace: Path


@dataclass(frozen=True)
class AutomaticBuildResult:
    selected_match: GeometryMatch
    portrait_record: Path
    uv_record: Path
    integrated: IntegratedBuildResult
    automatic_manifest: Path
    warnings: tuple[str, ...]


class AutomaticFaceBuilderService:
    """Run the implemented pipeline from one photograph using reviewed local resources.

    Initial portrait landmarks are estimates. Donor choice is evidence-backed by the
    calibrated geometry dataset, and only donors with a completed reviewed UV profile
    are eligible for the automatic build.
    """

    def build(self, inputs: AutomaticBuildInputs) -> AutomaticBuildResult:
        photo = Path(inputs.photo).expanduser().resolve()
        dataset_path = Path(inputs.geometry_dataset).expanduser().resolve()
        profiles = Path(inputs.uv_profiles_directory).expanduser().resolve()
        workspace = Path(inputs.workspace).expanduser().resolve()
        if not photo.is_file():
            raise ValueError(f"Photograph not found: {photo}")
        if not profiles.is_dir():
            raise ValueError(f"UV profile folder not found: {profiles}")
        workspace.mkdir(parents=True, exist_ok=True)

        portrait_service = OneClickFaceBuilder()
        analysis = portrait_service.analyse_photo(photo)
        portrait_record = portrait_service.save_analysis(
            analysis, workspace / f"{photo.stem}-automatic-landmarks"
        )

        geometry = GeometryDatasetService()
        records = geometry.load(dataset_path)
        matches = geometry.match(analysis.measurements, records, limit=max(10, len(records)))
        selected: GeometryMatch | None = None
        uv_record: Path | None = None
        for match in matches:
            candidate = self._find_uv_profile(profiles, match.player_id)
            if candidate is not None:
                selected, uv_record = match, candidate
                break
        if selected is None or uv_record is None:
            raise ValueError(
                "No geometry-matched donor has a completed UV calibration profile. "
                "Add reviewed donor profiles to the configured UV profile folder."
            )

        integrated = IntegratedFaceBuilderService().build(
            IntegratedBuildInputs(portrait_record, uv_record, workspace)
        )
        warnings = tuple(analysis.warnings) + (
            "Portrait landmarks were generated as automatic initial estimates and were not manually reviewed.",
            "Automatic readiness is advisory; inspect the preview before any controlled FM test.",
        )
        manifest = workspace / "facestudio-automatic-build.json"
        manifest.write_text(json.dumps({
            "format": AUTO_BUILD_FORMAT,
            "photo": str(photo),
            "portrait_record": str(portrait_record),
            "geometry_dataset": str(dataset_path),
            "selected_donor": selected.player_id,
            "geometry_score": selected.score,
            "geometry_distance": selected.distance,
            "uv_profile": str(uv_record),
            "integrated_manifest": str(integrated.project_manifest),
            "validation_score": integrated.validation_result.quality_score,
            "ready_for_controlled_testing": integrated.validation_result.ready_for_testing,
            "warnings": list(warnings),
            "accuracy_boundary": "Automatic estimated landmarks plus calibrated donor matching and reviewed UV profiles; no mesh or .skin generation.",
        }, indent=2), encoding="utf-8")
        return AutomaticBuildResult(selected, portrait_record, uv_record, integrated, manifest, warnings)

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

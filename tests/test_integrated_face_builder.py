from pathlib import Path
from types import SimpleNamespace

from facestudio.match_engine_research.integrated_face_builder import (
    IntegratedBuildInputs,
    IntegratedFaceBuilderService,
    PROJECT_FORMAT,
)


def test_integrated_inputs_have_reviewed_pipeline_defaults(tmp_path: Path):
    inputs = IntegratedBuildInputs(tmp_path / "portrait.json", tmp_path / "uv.json", tmp_path)
    assert inputs.transfer_strength == 0.92
    assert inputs.feather_radius == 6
    assert inputs.colour_matching == 0.65
    assert inputs.neighbour_blend == 0.35


def test_integrated_build_writes_traceable_manifest(tmp_path: Path, monkeypatch):
    reconstruction = SimpleNamespace(player_id="123", output=None)
    refined = SimpleNamespace()
    validation = SimpleNamespace(
        quality_score=88,
        ready_for_testing=True,
        refined_texture=str(tmp_path / "refined.png"),
    )

    monkeypatch.setattr(
        "facestudio.match_engine_research.integrated_face_builder.TextureReconstructionService.reconstruct",
        lambda self, portrait, uv, strength: reconstruction,
    )
    monkeypatch.setattr(
        "facestudio.match_engine_research.integrated_face_builder.TextureReconstructionService.save",
        lambda result, destination: (destination.with_suffix(".png"), destination.with_suffix(".json")),
    )
    monkeypatch.setattr(
        "facestudio.match_engine_research.integrated_face_builder.TextureRefinementService.refine",
        lambda self, manifest, settings: refined,
    )
    monkeypatch.setattr(
        "facestudio.match_engine_research.integrated_face_builder.TextureRefinementService.save",
        lambda result, destination: (destination.with_suffix(".png"), destination.with_suffix(".json")),
    )
    monkeypatch.setattr(
        "facestudio.match_engine_research.integrated_face_builder.TextureValidationService.validate",
        lambda self, manifest: validation,
    )
    monkeypatch.setattr(
        "facestudio.match_engine_research.integrated_face_builder.TextureValidationService.save_report",
        lambda result, destination: (destination, destination, destination),
    )
    monkeypatch.setattr(
        "facestudio.match_engine_research.integrated_face_builder.TextureValidationService.create_test_package",
        lambda result, destination: destination / "facestudio-test-123",
    )

    result = IntegratedFaceBuilderService().build(
        IntegratedBuildInputs(tmp_path / "portrait.json", tmp_path / "uv.json", tmp_path)
    )
    payload = result.project_manifest.read_text(encoding="utf-8")
    assert PROJECT_FORMAT in payload
    assert '"player_id": "123"' in payload
    assert result.package_directory == tmp_path / "facestudio-test-123"


def test_integrated_build_does_not_package_failed_validation(tmp_path: Path, monkeypatch):
    reconstruction = SimpleNamespace(player_id="456", output=None)
    validation = SimpleNamespace(quality_score=61, ready_for_testing=False, refined_texture="x.png")
    monkeypatch.setattr("facestudio.match_engine_research.integrated_face_builder.TextureReconstructionService.reconstruct", lambda *args: reconstruction)
    monkeypatch.setattr("facestudio.match_engine_research.integrated_face_builder.TextureReconstructionService.save", lambda result, destination: (destination.with_suffix(".png"), destination.with_suffix(".json")))
    monkeypatch.setattr("facestudio.match_engine_research.integrated_face_builder.TextureRefinementService.refine", lambda *args: SimpleNamespace())
    monkeypatch.setattr("facestudio.match_engine_research.integrated_face_builder.TextureRefinementService.save", lambda result, destination: (destination.with_suffix(".png"), destination.with_suffix(".json")))
    monkeypatch.setattr("facestudio.match_engine_research.integrated_face_builder.TextureValidationService.validate", lambda *args: validation)
    monkeypatch.setattr("facestudio.match_engine_research.integrated_face_builder.TextureValidationService.save_report", lambda *args: (Path("a"), Path("b"), Path("c")))
    result = IntegratedFaceBuilderService().build(IntegratedBuildInputs(Path("portrait.json"), Path("uv.json"), tmp_path))
    assert result.package_directory is None

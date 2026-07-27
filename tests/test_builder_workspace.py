from pathlib import Path

import pytest

from facestudio.match_engine_research.builder_workspace import (
    BuilderWorkspace, STAGES, WORKSPACE_FORMAT,
)


def test_workspace_contains_every_builder_page():
    workspace = BuilderWorkspace()
    assert tuple(workspace.stages) == STAGES
    assert workspace.stages["home"].status == "complete"
    assert workspace.stages["landmarks"].status == "needs-review"
    assert workspace.stages["export"].status == "blocked"


def test_workspace_progress_and_persistence(tmp_path: Path):
    source = tmp_path / "portrait.png"; source.write_bytes(b"image")
    landmarks = tmp_path / "landmarks.json"; landmarks.write_text("{}", encoding="utf-8")
    uv = tmp_path / "uv.json"; uv.write_text("{}", encoding="utf-8")
    workspace = BuilderWorkspace(
        project_name="Test Player",
        workspace_directory=str(tmp_path),
        source_photo=str(source),
        portrait_record=str(landmarks),
        uv_record=str(uv),
    )
    assert workspace.progress > 0
    path = workspace.save(tmp_path / "workspace.json")
    assert WORKSPACE_FORMAT in path.read_text(encoding="utf-8")
    loaded = BuilderWorkspace.load(path)
    assert loaded.project_name == "Test Player"
    assert loaded.stages["source_photo"].status == "complete"
    assert loaded.stages["uv_calibration"].status == "complete"


def test_invalid_workspace_format_is_rejected(tmp_path: Path):
    path = tmp_path / "workspace.json"
    path.write_text('{"format":"wrong"}', encoding="utf-8")
    with pytest.raises(ValueError, match="facestudio-builder-workspace-v1"):
        BuilderWorkspace.load(path)


def test_integrated_build_marks_final_pages_complete(tmp_path: Path):
    manifest = tmp_path / "facestudio-integrated-build.json"
    manifest.write_text("{}", encoding="utf-8")
    workspace = BuilderWorkspace(workspace_directory=str(tmp_path))
    workspace.record_integrated_build(manifest)
    assert workspace.stages["reconstruction"].status == "complete"
    assert workspace.stages["refinement"].status == "complete"
    assert workspace.stages["validation"].status == "complete"
    assert workspace.stages["preview"].status == "complete"
    assert workspace.stages["export"].status == "complete"

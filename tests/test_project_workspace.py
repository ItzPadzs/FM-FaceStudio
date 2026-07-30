from __future__ import annotations

import json
from pathlib import Path

import pytest

from facestudio.project_workspace import PROJECT_FORMAT, FaceStudioProject


def test_project_round_trip_preserves_paths_and_settings(tmp_path: Path) -> None:
    portrait = tmp_path / "portrait.png"
    donor = tmp_path / "donor.png"
    generated = tmp_path / "generated.png"
    for path in (portrait, donor, generated):
        path.write_bytes(b"fixture")

    project = FaceStudioProject(
        name="Example Player",
        directory=tmp_path / "Example Player",
        portrait=portrait,
        donor_texture=donor,
        generated_texture=generated,
        mask_profile="fm-default-v1",
        colour_strength=0.72,
        diagnostics=[tmp_path / "confidence.png"],
    )

    manifest = project.save()
    restored = FaceStudioProject.load(manifest)

    assert restored.name == "Example Player"
    assert restored.portrait == portrait
    assert restored.donor_texture == donor
    assert restored.generated_texture == generated
    assert restored.mask_profile == "fm-default-v1"
    assert restored.colour_strength == 0.72
    assert restored.diagnostics == [tmp_path / "confidence.png"]
    assert restored.output_directory.is_dir()
    assert restored.diagnostics_directory.is_dir()

    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert payload["format"] == PROJECT_FORMAT


def test_project_rejects_invalid_colour_strength(tmp_path: Path) -> None:
    project = FaceStudioProject(
        name="Invalid",
        directory=tmp_path / "invalid",
        colour_strength=1.5,
    )

    with pytest.raises(ValueError, match="Colour strength"):
        project.save()


def test_project_rejects_empty_name(tmp_path: Path) -> None:
    project = FaceStudioProject(name="   ", directory=tmp_path / "empty")

    with pytest.raises(ValueError, match="name"):
        project.save()

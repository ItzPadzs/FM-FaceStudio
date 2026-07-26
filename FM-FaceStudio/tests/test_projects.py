from pathlib import Path
from facestudio.projects.model import FaceStudioProject


def test_project_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "player.facestudio"
    project = FaceStudioProject(name="Test Player", source_photo="photo.jpg")
    project.save(path)
    assert FaceStudioProject.load(path) == project

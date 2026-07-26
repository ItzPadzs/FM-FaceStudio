from pathlib import Path

from facestudio.projects.model import FaceStudioProject
from facestudio.projects.service import ProjectService


def test_project_directory_round_trip(tmp_path: Path) -> None:
    directory = tmp_path / "player.facestudio"
    service = ProjectService()
    project = service.create(directory, "Test Player")
    project.notes = "Goalkeeper"
    service.save(project, directory)

    loaded = service.open(directory)
    assert loaded.name == "Test Player"
    assert loaded.notes == "Goalkeeper"
    assert (directory / "project.json").exists()
    assert (directory / "generated").is_dir()


def test_import_source_photo(tmp_path: Path) -> None:
    source = tmp_path / "photo.jpg"
    source.write_bytes(b"fake image bytes")

    directory = tmp_path / "player.facestudio"
    service = ProjectService()
    project = service.create(directory, "Test Player")
    destination = service.import_source_photo(
        project,
        directory,
        source,
    )

    assert destination.exists()
    assert project.source_photo == "source/source_photo.jpg"

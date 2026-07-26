from __future__ import annotations

import shutil
from pathlib import Path

from facestudio.projects.model import FaceStudioProject


class ProjectService:
    def create(self, directory: Path, name: str) -> FaceStudioProject:
        name = name.strip()
        if not name:
            raise ValueError("Project name cannot be empty.")

        directory.mkdir(parents=True, exist_ok=True)
        project = FaceStudioProject(name=name)
        project.save_to_directory(directory)
        return project

    def open(self, directory: Path) -> FaceStudioProject:
        return FaceStudioProject.load_from_directory(directory)

    def save(self, project: FaceStudioProject, directory: Path) -> Path:
        return project.save_to_directory(directory)

    def import_source_photo(
        self,
        project: FaceStudioProject,
        project_directory: Path,
        source_path: Path,
    ) -> Path:
        if not source_path.exists() or not source_path.is_file():
            raise FileNotFoundError(source_path)

        source_dir = project_directory / "source"
        source_dir.mkdir(parents=True, exist_ok=True)

        extension = source_path.suffix.lower() or ".jpg"
        destination = source_dir / f"source_photo{extension}"
        shutil.copy2(source_path, destination)

        project.source_photo = str(destination.relative_to(project_directory))
        project.save_to_directory(project_directory)
        return destination

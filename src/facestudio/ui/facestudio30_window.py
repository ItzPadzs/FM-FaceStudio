from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QVBoxLayout

from facestudio.project_workspace import FaceStudioProject
from facestudio.ui.facestudio21_window import FaceStudio21Window


class FaceStudio30Window(FaceStudio21Window):
    """Project-based FaceStudio workspace layered over the existing generator UI."""

    def __init__(self, config, config_path: Path) -> None:
        self.project: FaceStudioProject | None = None
        self.projects_root = config_path.parent / "projects"
        super().__init__(config, config_path)
        self.setWindowTitle("FM FaceStudio — 3.0 Project Workspace")
        self._install_project_bar()

    def _install_project_bar(self) -> None:
        bar = QFrame()
        bar.setObjectName("Card")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.addWidget(QLabel("PROJECT"))
        self.project_name = QLineEdit()
        self.project_name.setPlaceholderText("Player or project name")
        layout.addWidget(self.project_name, 1)
        new_button = QPushButton("New Project")
        new_button.clicked.connect(self.new_project)
        layout.addWidget(new_button)
        open_button = QPushButton("Open Project")
        open_button.clicked.connect(self.open_project)
        layout.addWidget(open_button)
        save_button = QPushButton("Save Project")
        save_button.clicked.connect(self.save_project)
        layout.addWidget(save_button)
        self.page_layout.insertWidget(0, bar)

    def new_project(self) -> None:
        name = self.project_name.text().strip()
        if not name:
            QMessageBox.information(self, "New project", "Enter a project name first.")
            return
        safe_name = "".join(character if character.isalnum() or character in "-_ " else "_" for character in name).strip()
        directory = self.projects_root / safe_name
        self.project = FaceStudioProject(name=name, directory=directory)
        self.project.save()
        self.status.setText(f"Project created: {directory}")

    def open_project(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(self, "Open FaceStudio project", str(self.projects_root), "FaceStudio project (project.json)")
        if not filename:
            return
        try:
            self.project = FaceStudioProject.load(Path(filename))
            self.project_name.setText(self.project.name)
            if self.project.portrait and self.project.portrait.is_file():
                self.photo = self.project.portrait
                self.photo_card.setText(f"{self.photo.name}\n{self.photo.parent}")
                self._set_preview(self.source_preview, self.photo, 560, 430)
            if self.project.generated_texture and self.project.generated_texture.is_file():
                self._set_preview(self.texture_preview, self.project.generated_texture, 680, 430)
            self.status.setText(f"Project opened: {self.project.directory}")
        except Exception as exc:
            QMessageBox.critical(self, "Could not open project", str(exc))

    def save_project(self) -> None:
        if self.project is None:
            self.new_project()
            if self.project is None:
                return
        self.project.name = self.project_name.text().strip() or self.project.name
        self.project.portrait = self.photo
        self.project.save()
        self.status.setText(f"Project saved: {self.project.manifest_path}")

    def choose_photo(self) -> None:
        super().choose_photo()
        if self.project is not None and self.photo is not None:
            self.project.portrait = self.photo
            self.project.save()

    def start_generation(self) -> None:
        super().start_generation()
        if self.project is not None and self.photo is not None:
            output = self.output_dir / f"{self.photo.stem}-facestudio2.png"
            if output.is_file():
                self.project.generated_texture = output
                self.project.save()

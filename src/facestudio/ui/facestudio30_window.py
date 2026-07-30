from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QDialog, QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton

from facestudio.project_workspace import FaceStudioProject
from facestudio.ui.facestudio21_window import FaceStudio21Window
from facestudio.ui.five_point_alignment import FivePointAlignmentDialog


class FaceStudio30Window(FaceStudio21Window):
    """Project workspace with UI-assisted, five-point portrait alignment."""

    def __init__(self, config, config_path: Path) -> None:
        self.project: FaceStudioProject | None = None
        self.projects_root = config_path.parent / "projects"
        self.original_photo: Path | None = None
        super().__init__(config, config_path)
        self.setWindowTitle("FM FaceStudio — 3.1 Five-Point Alignment")
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

        self.align_button = QPushButton("Align Portrait")
        self.align_button.setEnabled(False)
        self.align_button.clicked.connect(self.open_alignment_editor)
        layout.addWidget(self.align_button)

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
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Open FaceStudio project",
            str(self.projects_root),
            "FaceStudio project (project.json)",
        )
        if not filename:
            return
        try:
            self.project = FaceStudioProject.load(Path(filename))
            self.project_name.setText(self.project.name)
            self.original_photo = self.project.portrait
            active_photo = self.project.aligned_portrait or self.project.portrait
            if active_photo and active_photo.is_file():
                self.photo = active_photo
                self.photo_card.setText(f"{active_photo.name}\n{active_photo.parent}")
                self._set_preview(self.source_preview, active_photo, 560, 430)
                self.align_button.setEnabled(self.original_photo is not None)
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
        self.project.portrait = self.original_photo or self.photo
        if self.photo and self.original_photo and self.photo != self.original_photo:
            self.project.aligned_portrait = self.photo
        self.project.save()
        self.status.setText(f"Project saved: {self.project.manifest_path}")

    def choose_photo(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Choose portrait",
            "",
            "Images (*.png *.jpg *.jpeg *.webp *.bmp)",
        )
        if not filename:
            return
        self.original_photo = Path(filename)
        self.photo = self.original_photo
        self.photo_card.setText(f"{self.photo.name}\n{self.photo.parent}")
        self._set_preview(self.source_preview, self.photo, 560, 430)
        self.align_button.setEnabled(True)

        if self.project is not None:
            self.project.portrait = self.original_photo
            self.project.aligned_portrait = None
            self.project.alignment_landmarks = {}
            self.project.save()

        if self.pipeline is None:
            answer = QMessageBox.question(
                self,
                "Set up FaceStudio assets",
                "Choose a folder of working FM textures now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            )
            if answer == QMessageBox.StandardButton.Yes:
                self.choose_index()
            else:
                self.status.setText("Portrait loaded. Import a working FM texture folder, then align the portrait.")
                return

        self.open_alignment_editor()

    def open_alignment_editor(self) -> None:
        source = self.original_photo or self.photo
        if source is None or not source.is_file():
            QMessageBox.information(self, "Five-point alignment", "Upload a portrait first.")
            return
        dialog = FivePointAlignmentDialog(source, self)
        if dialog.exec() != QDialog.DialogCode.Accepted or dialog.selection is None:
            self.status.setText("Portrait loaded. Alignment was not changed.")
            return

        if self.project is None:
            name = self.project_name.text().strip() or source.stem
            self.project_name.setText(name)
            safe_name = "".join(character if character.isalnum() or character in "-_ " else "_" for character in name).strip()
            self.project = FaceStudioProject(name=name, directory=self.projects_root / safe_name)

        aligned_path = self.project.alignment_directory / "aligned-portrait.png"
        aligned_path.parent.mkdir(parents=True, exist_ok=True)
        if not dialog.selection.aligned_image.save(str(aligned_path), "PNG"):
            QMessageBox.critical(self, "Alignment failed", f"Could not save aligned portrait: {aligned_path}")
            return

        self.photo = aligned_path
        self.project.portrait = source
        self.project.aligned_portrait = aligned_path
        self.project.alignment_landmarks = dialog.selection.normalised(dialog.source.width(), dialog.source.height())
        self.project.save()
        self.photo_card.setText(f"Aligned: {aligned_path.name}\nSource: {source.name}")
        self._set_preview(self.source_preview, aligned_path, 560, 430)
        self.status.setText("Five-point alignment confirmed. Starting UV-safe generation…")
        self.start_generation()

    def start_generation(self) -> None:
        super().start_generation()
        if self.project is not None and self.photo is not None:
            output = self.output_dir / f"{self.photo.stem}-facestudio2.png"
            if output.is_file():
                self.project.generated_texture = output
                self.project.save()

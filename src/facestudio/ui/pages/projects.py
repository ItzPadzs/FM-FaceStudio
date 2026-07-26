from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from facestudio.projects.model import FaceStudioProject


class ProjectsPage(QWidget):
    project_edited = Signal()
    save_requested = Signal()
    import_photo_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._loading = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 28, 30, 28)
        layout.setSpacing(14)

        title = QLabel("Project")
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        self.empty_label = QLabel("No project is open.")
        self.empty_label.setObjectName("Muted")
        layout.addWidget(self.empty_label)

        self.editor = QWidget()
        editor_layout = QVBoxLayout(self.editor)
        editor_layout.setContentsMargins(0, 0, 0, 0)

        details = QGroupBox("Project details")
        details_form = QFormLayout(details)

        self.name_edit = QLineEdit()
        self.name_edit.textEdited.connect(self.project_edited.emit)
        details_form.addRow("Player / project name", self.name_edit)

        self.notes_edit = QPlainTextEdit()
        self.notes_edit.setPlaceholderText(
            "Optional notes about the player, club, position or target appearance."
        )
        self.notes_edit.textChanged.connect(self._notes_changed)
        details_form.addRow("Notes", self.notes_edit)
        editor_layout.addWidget(details)

        source = QGroupBox("Source photograph")
        source_layout = QHBoxLayout(source)
        self.photo_preview = QLabel("No photo imported")
        self.photo_preview.setMinimumSize(220, 220)
        self.photo_preview.setMaximumSize(320, 320)
        self.photo_preview.setScaledContents(False)
        self.photo_preview.setAlignment(
            __import__("PySide6.QtCore", fromlist=["Qt"]).Qt.AlignmentFlag.AlignCenter
        )
        self.photo_preview.setStyleSheet(
            "border: 1px dashed #4a505b; border-radius: 8px;"
        )
        source_layout.addWidget(self.photo_preview)

        source_actions = QVBoxLayout()
        import_button = QPushButton("Import photograph…")
        import_button.setObjectName("Primary")
        import_button.clicked.connect(self.import_photo_requested.emit)
        self.photo_path = QLabel("")
        self.photo_path.setObjectName("Muted")
        self.photo_path.setWordWrap(True)
        source_actions.addWidget(import_button)
        source_actions.addWidget(self.photo_path)
        source_actions.addStretch()
        source_layout.addLayout(source_actions)
        editor_layout.addWidget(source)

        buttons = QHBoxLayout()
        save_button = QPushButton("Save Project")
        save_button.setObjectName("Primary")
        save_button.clicked.connect(self.save_requested.emit)
        buttons.addStretch()
        buttons.addWidget(save_button)
        editor_layout.addLayout(buttons)

        layout.addWidget(self.editor)
        layout.addStretch()
        self.set_project(None, None)

    def _notes_changed(self) -> None:
        if not self._loading:
            self.project_edited.emit()

    def set_project(
        self,
        project: FaceStudioProject | None,
        directory: Path | None,
    ) -> None:
        self._loading = True
        try:
            has_project = project is not None and directory is not None
            self.empty_label.setVisible(not has_project)
            self.editor.setVisible(has_project)
            if not has_project:
                self.name_edit.clear()
                self.notes_edit.clear()
                self.photo_path.clear()
                self.photo_preview.setPixmap(QPixmap())
                self.photo_preview.setText("No photo imported")
                return

            self.name_edit.setText(project.name)
            self.notes_edit.setPlainText(project.notes)
            self._set_photo(project, directory)
        finally:
            self._loading = False

    def _set_photo(
        self,
        project: FaceStudioProject,
        directory: Path,
    ) -> None:
        if not project.source_photo:
            self.photo_path.setText("No source photograph imported.")
            self.photo_preview.setPixmap(QPixmap())
            self.photo_preview.setText("No photo imported")
            return

        path = directory / project.source_photo
        self.photo_path.setText(str(path))
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            self.photo_preview.setText("Unable to preview image")
            return

        scaled = pixmap.scaled(
            300,
            300,
            __import__("PySide6.QtCore", fromlist=["Qt"]).Qt.AspectRatioMode.KeepAspectRatio,
            __import__("PySide6.QtCore", fromlist=["Qt"]).Qt.TransformationMode.SmoothTransformation,
        )
        self.photo_preview.setPixmap(scaled)
        self.photo_preview.setText("")

    def apply_to_project(self, project: FaceStudioProject) -> None:
        project.name = self.name_edit.text().strip() or "Untitled Project"
        project.notes = self.notes_edit.toPlainText().strip()

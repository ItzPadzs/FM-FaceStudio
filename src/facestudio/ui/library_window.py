from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QFrame, QMessageBox, QPushButton, QVBoxLayout

from facestudio.library.store import FaceLibraryStore
from facestudio.ui.alpha_window import AlphaMainWindow
from facestudio.ui.pages.face_library import FaceLibraryPage
from facestudio.utils.config import AppConfig


class LibraryMainWindow(AlphaMainWindow):
    """Alpha 0.9 shell with a persistent reusable Face Library workspace."""

    def __init__(self, config: AppConfig, config_path: Path) -> None:
        super().__init__(config, config_path)
        self.face_library_store = FaceLibraryStore(config_path.parent / "face-library.json")
        self.face_library = FaceLibraryPage(self.face_library_store)
        self.face_library.add_current_requested.connect(self.add_current_face_to_library)
        self.face_library.open_project_requested.connect(
            lambda path: self.open_project(Path(path))
        )

        page_index = self.stack.count()
        self.stack.addWidget(self.face_library)
        library_button = QPushButton("Face Library")
        library_button.setObjectName("NavButton")
        library_button.setCheckable(True)
        library_button.clicked.connect(
            lambda checked=False, index=page_index: self.navigate(index)
        )
        self.nav_buttons.append(library_button)

        sidebar = self.findChild(QFrame, "Sidebar")
        layout = sidebar.layout() if sidebar is not None else None
        if isinstance(layout, QVBoxLayout):
            # Keep the library with the main workspaces, above the project summary.
            layout.insertWidget(max(0, layout.count() - 3), library_button)

        self.apply_theme(self.config.theme)

    def add_current_face_to_library(self) -> None:
        if not self.session.is_open:
            QMessageBox.information(
                self,
                "No project open",
                "Open a project with a completed face analysis first.",
            )
            return

        project = self.session.project
        directory = self.session.directory
        if not project.analysis_file or not (directory / project.analysis_file).exists():
            QMessageBox.information(
                self,
                "Analysis required",
                "Run Face Analysis for the current project before adding it to the library.",
            )
            return

        try:
            record = self.face_library_store.add_project(
                project.name,
                directory,
                project.source_photo,
                project.preview_file,
                project.analysis_file,
            )
        except (OSError, ValueError, KeyError, TypeError) as exc:
            QMessageBox.critical(self, "Unable to add face", str(exc))
            return

        self.face_library.refresh()
        self.status.showMessage(f"Added {record.name} to the Face Library.", 4000)

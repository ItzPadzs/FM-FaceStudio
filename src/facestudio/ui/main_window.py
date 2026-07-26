from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QSize, QTimer
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from facestudio.projects.recent import RecentProject, RecentProjectsStore
from facestudio.projects.service import ProjectService
from facestudio.projects.session import ProjectSession
from facestudio.ui.pages.about import AboutPage
from facestudio.ui.pages.base import PlaceholderPage
from facestudio.ui.pages.dashboard import DashboardPage
from facestudio.ui.pages.projects import ProjectsPage
from facestudio.ui.pages.settings import SettingsPage
from facestudio.ui.theme import DARK_STYLESHEET, LIGHT_STYLESHEET
from facestudio.utils.config import AppConfig

LOGGER = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(self, config: AppConfig, config_path: Path) -> None:
        super().__init__()
        self.config = config
        self.config_path = config_path
        self.project_service = ProjectService()
        self.session = ProjectSession()
        self.recent_store = RecentProjectsStore(
            config_path.parent / "recent-projects.json"
        )

        self.setWindowTitle("FM FaceStudio — Sprint 2")
        self.resize(1180, 760)
        self.setMinimumSize(QSize(920, 620))

        self.status = QStatusBar()
        self.setStatusBar(self.status)

        root = QWidget()
        self.setCentralWidget(root)
        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(230)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(16, 20, 16, 18)

        brand = QLabel("FM FaceStudio")
        brand.setObjectName("Brand")
        side.addWidget(brand)
        sprint = QLabel("SPRINT 2")
        sprint.setObjectName("Muted")
        side.addWidget(sprint)
        side.addSpacing(16)

        self.stack = QStackedWidget()

        self.dashboard = DashboardPage()
        self.dashboard.new_project_requested.connect(self.create_project)
        self.dashboard.open_project_requested.connect(self.open_project_dialog)
        self.dashboard.recent_project_requested.connect(
            lambda path: self.open_project(Path(path))
        )

        self.projects_page = ProjectsPage()
        self.projects_page.project_edited.connect(self.mark_dirty)
        self.projects_page.save_requested.connect(self.save_project)
        self.projects_page.import_photo_requested.connect(self.import_photo)

        settings = SettingsPage(config)
        settings.theme_changed.connect(self.apply_theme)
        settings.settings_changed.connect(self.save_config)

        pages = [
            ("Dashboard", self.dashboard),
            ("Project", self.projects_page),
            ("Face AI", PlaceholderPage("Face AI", "Analyse a source photograph and create a reusable face descriptor.", "Planned for Sprint 5.")),
            ("Asset Explorer", PlaceholderPage("Asset Explorer", "Index and browse FM26 appearance assets.", "Planned for Sprint 3.")),
            ("Mesh Viewer", PlaceholderPage("Mesh Viewer", "Inspect supported meshes in an interactive viewport.", "Planned for Sprint 4.")),
            ("Export", PlaceholderPage("Export Centre", "Build validated packages with backup and restore.", "Disabled until game formats are fully validated.")),
            ("Settings", settings),
            ("About", AboutPage()),
        ]

        self.nav_buttons: list[QPushButton] = []
        for index, (label, page) in enumerate(pages):
            self.stack.addWidget(page)
            button = QPushButton(label)
            button.setCheckable(True)
            button.clicked.connect(
                lambda checked=False, i=index: self.navigate(i)
            )
            self.nav_buttons.append(button)
            side.addWidget(button)

        side.addStretch()
        self.project_label = QLabel("No project open")
        self.project_label.setObjectName("Muted")
        self.project_label.setWordWrap(True)
        side.addWidget(self.project_label)

        outer.addWidget(sidebar)
        outer.addWidget(self.stack, 1)

        self.autosave_timer = QTimer(self)
        self.autosave_timer.timeout.connect(self.autosave)
        self.configure_autosave()

        self.refresh_recent_projects()
        self.navigate(0)
        self.apply_theme(config.theme)
        LOGGER.info("Sprint 2 main window initialised")

        if config.last_project_path:
            candidate = Path(config.last_project_path)
            if candidate.exists():
                self.status.showMessage(
                    "Last project is available from Recent Projects.",
                    5000,
                )

    def navigate(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        for i, button in enumerate(self.nav_buttons):
            button.setChecked(i == index)

    def apply_theme(self, theme: str) -> None:
        self.config.theme = theme
        self.setStyleSheet(
            LIGHT_STYLESHEET if theme == "light" else DARK_STYLESHEET
        )

    def create_project(self) -> None:
        if not self._confirm_discard_if_needed():
            return

        name, accepted = QInputDialog.getText(
            self,
            "New FaceStudio Project",
            "Player or project name:",
        )
        if not accepted or not name.strip():
            return

        parent = QFileDialog.getExistingDirectory(
            self,
            "Choose where to create the project",
        )
        if not parent:
            return

        safe_name = "".join(
            ch for ch in name.strip() if ch not in '<>:"/\\|?*'
        ).strip() or "Untitled Project"
        directory = Path(parent) / f"{safe_name}.facestudio"

        if directory.exists() and any(directory.iterdir()):
            QMessageBox.warning(
                self,
                "Project already exists",
                f"The folder already exists and is not empty:\n{directory}",
            )
            return

        try:
            project = self.project_service.create(directory, name)
        except (OSError, ValueError) as exc:
            QMessageBox.critical(
                self,
                "Unable to create project",
                str(exc),
            )
            return

        self._set_session(project, directory)
        self.status.showMessage("Project created.", 4000)
        self.navigate(1)

    def open_project_dialog(self) -> None:
        if not self._confirm_discard_if_needed():
            return

        directory = QFileDialog.getExistingDirectory(
            self,
            "Open FaceStudio Project",
        )
        if directory:
            self.open_project(Path(directory))

    def open_project(self, directory: Path) -> None:
        if self.session.directory != directory:
            if not self._confirm_discard_if_needed():
                return

        try:
            project = self.project_service.open(directory)
        except (OSError, ValueError) as exc:
            QMessageBox.critical(
                self,
                "Unable to open project",
                f"{exc}\n\nChoose a folder containing project.json.",
            )
            self.refresh_recent_projects()
            return

        self._set_session(project, directory)
        self.status.showMessage("Project opened.", 4000)
        self.navigate(1)

    def _set_session(self, project, directory: Path) -> None:
        self.session.project = project
        self.session.directory = directory
        self.session.dirty = False

        self.projects_page.set_project(project, directory)
        self.project_label.setText(f"{project.name}\n{directory}")
        self.setWindowTitle(f"{project.name} — FM FaceStudio")
        self.config.last_project_path = str(directory)

        self.recent_store.add(
            RecentProject(name=project.name, path=str(directory))
        )
        self.refresh_recent_projects()
        self.save_config()

    def mark_dirty(self) -> None:
        if not self.session.is_open:
            return

        self.projects_page.apply_to_project(self.session.project)
        self.session.dirty = True
        self.project_label.setText(
            f"{self.session.project.name} *\n{self.session.directory}"
        )
        self.setWindowTitle(
            f"{self.session.project.name} * — FM FaceStudio"
        )

    def save_project(self, silent: bool = False) -> bool:
        if not self.session.is_open:
            if not silent:
                QMessageBox.information(
                    self,
                    "No project",
                    "Create or open a project first.",
                )
            return False

        self.projects_page.apply_to_project(self.session.project)

        try:
            self.project_service.save(
                self.session.project,
                self.session.directory,
            )
        except OSError as exc:
            if not silent:
                QMessageBox.critical(
                    self,
                    "Unable to save project",
                    str(exc),
                )
            LOGGER.exception("Project save failed")
            return False

        self.session.dirty = False
        self.project_label.setText(
            f"{self.session.project.name}\n{self.session.directory}"
        )
        self.setWindowTitle(
            f"{self.session.project.name} — FM FaceStudio"
        )
        self.recent_store.add(
            RecentProject(
                name=self.session.project.name,
                path=str(self.session.directory),
            )
        )
        self.refresh_recent_projects()
        self.status.showMessage(
            "Autosaved." if silent else "Project saved.",
            2500,
        )
        return True

    def import_photo(self) -> None:
        if not self.session.is_open:
            QMessageBox.information(
                self,
                "No project",
                "Create or open a project first.",
            )
            return

        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Import source photograph",
            "",
            "Images (*.jpg *.jpeg *.png *.webp *.bmp)",
        )
        if not filename:
            return

        try:
            self.project_service.import_source_photo(
                self.session.project,
                self.session.directory,
                Path(filename),
            )
        except OSError as exc:
            QMessageBox.critical(
                self,
                "Unable to import photograph",
                str(exc),
            )
            return

        self.session.dirty = False
        self.projects_page.set_project(
            self.session.project,
            self.session.directory,
        )
        self.status.showMessage("Photograph imported.", 4000)

    def configure_autosave(self) -> None:
        self.autosave_timer.stop()
        if self.config.autosave_enabled:
            interval_ms = max(
                15,
                self.config.autosave_interval_seconds,
            ) * 1000
            self.autosave_timer.start(interval_ms)

    def autosave(self) -> None:
        if (
            self.config.autosave_enabled
            and self.session.is_open
            and self.session.dirty
        ):
            self.save_project(silent=True)

    def refresh_recent_projects(self) -> None:
        projects = self.recent_store.remove_missing()
        self.dashboard.set_recent_projects(projects)

    def save_config(self) -> None:
        try:
            self.config.save(self.config_path)
            self.configure_autosave()
        except OSError as exc:
            LOGGER.exception("Settings save failed")
            QMessageBox.warning(
                self,
                "Settings",
                f"Settings could not be saved:\n{exc}",
            )

    def _confirm_discard_if_needed(self) -> bool:
        if not self.session.dirty:
            return True

        choice = QMessageBox.question(
            self,
            "Unsaved changes",
            "Save changes to the current project before continuing?",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )

        if choice == QMessageBox.StandardButton.Save:
            return self.save_project()
        if choice == QMessageBox.StandardButton.Discard:
            return True
        return False

    def closeEvent(self, event) -> None:
        if not self._confirm_discard_if_needed():
            event.ignore()
            return
        self.save_config()
        event.accept()

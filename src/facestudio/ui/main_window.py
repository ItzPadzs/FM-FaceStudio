from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QSize, QThread, QTimer
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

from facestudio.assets.database import AssetDatabase
from facestudio.projects.recent import RecentProject, RecentProjectsStore
from facestudio.projects.service import ProjectService
from facestudio.projects.session import ProjectSession
from facestudio.ui.pages.about import AboutPage
from facestudio.ui.pages.asset_explorer import AssetExplorerPage
from facestudio.ui.pages.base import PlaceholderPage
from facestudio.ui.pages.dashboard import DashboardPage
from facestudio.ui.pages.projects import ProjectsPage
from facestudio.ui.pages.mesh_viewer import MeshViewerPage
from facestudio.ui.pages.face_analysis import FaceAnalysisPage
from facestudio.ui.pages.face_matcher import FaceMatcherPage
from facestudio.ui.pages.settings import SettingsPage
from facestudio.ui.theme import DARK_STYLESHEET, LIGHT_STYLESHEET
from facestudio.ui.workers import (
    AssetScanWorker,
    FaceAnalysisWorker,
    FaceMatchingWorker,
)
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
        self.asset_database = AssetDatabase(
            config_path.parent / "assets.sqlite3"
        )
        self.scan_thread: QThread | None = None
        self.scan_worker: AssetScanWorker | None = None
        self.analysis_thread: QThread | None = None
        self.analysis_worker: FaceAnalysisWorker | None = None
        self.match_thread: QThread | None = None
        self.match_worker: FaceMatchingWorker | None = None

        self.setWindowTitle("FM FaceStudio — Sprint 6")
        self.resize(1240, 800)
        self.setMinimumSize(QSize(960, 640))

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
        sprint = QLabel("SPRINT 6")
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

        self.asset_explorer = AssetExplorerPage(self.asset_database)
        self.asset_explorer.scan_requested.connect(self.start_asset_scan)
        self.asset_explorer.cancel_requested.connect(self.cancel_asset_scan)
        self.asset_explorer.asset_open_requested.connect(self.open_asset_in_mesh_viewer)
        if config.fm_install_path:
            self.asset_explorer.root_path.setText(config.fm_install_path)

        self.mesh_viewer = MeshViewerPage()
        self.mesh_viewer.status_message.connect(self.status.showMessage)

        self.face_analysis = FaceAnalysisPage()
        self.face_analysis.analyze_requested.connect(self.start_face_analysis)

        catalogue_path = (
            Path(__file__).resolve().parents[3]
            / "data"
            / "sample_face_catalogue.json"
        )
        self.face_matcher = FaceMatcherPage(catalogue_path)
        self.face_matcher.match_requested.connect(self.start_face_matching)

        settings = SettingsPage(config)
        settings.theme_changed.connect(self.apply_theme)
        settings.settings_changed.connect(self.save_config)

        pages = [
            ("Dashboard", self.dashboard),
            ("Project", self.projects_page),
            ("Asset Explorer", self.asset_explorer),
            ("Mesh Explorer", self.mesh_viewer),
            ("Face Analysis", self.face_analysis),
            ("Face Matcher", self.face_matcher),
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
        LOGGER.info("Sprint 6 main window initialised")

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
            QMessageBox.critical(self, "Unable to create project", str(exc))
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
        self.face_analysis.set_project(project, directory)
        self.face_matcher.set_project(project, directory)
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
        self.face_analysis.set_project(
            self.session.project,
            self.session.directory,
        )
        self.face_matcher.set_project(
            self.session.project,
            self.session.directory,
        )
        self.status.showMessage("Photograph imported.", 4000)

    def open_asset_in_mesh_viewer(self, path: str) -> None:
        self.mesh_viewer.open_path(Path(path))
        self.navigate(3)

    def start_face_analysis(self) -> None:
        if not self.session.is_open or not self.session.project.source_photo:
            QMessageBox.information(
                self,
                "Source photograph required",
                "Open a project and import a source photograph first.",
            )
            return
        if self.analysis_thread is not None:
            return

        source_path = (
            self.session.directory / self.session.project.source_photo
        )
        thread = QThread(self)
        worker = FaceAnalysisWorker(source_path, self.session.directory)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.progress.connect(
            lambda message: self.face_analysis.set_busy(True, message)
        )
        worker.completed.connect(self._face_analysis_completed)
        worker.failed.connect(self._face_analysis_failed)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._face_analysis_thread_finished)

        self.analysis_thread = thread
        self.analysis_worker = worker
        self.face_analysis.set_busy(True, "Starting face analysis…")
        self.status.showMessage("Analysing source photograph…")
        thread.start()

    def _face_analysis_completed(
        self,
        analysis,
        analysis_path: str,
        preview_path: str,
    ) -> None:
        self.session.project.analysis_file = str(
            Path(analysis_path).relative_to(self.session.directory)
        )
        self.session.project.preview_file = str(
            Path(preview_path).relative_to(self.session.directory)
        )
        self.project_service.save(
            self.session.project,
            self.session.directory,
        )
        self.session.dirty = False
        self.face_analysis.show_analysis(
            analysis,
            Path(preview_path),
        )
        self.face_matcher.set_project(
            self.session.project,
            self.session.directory,
        )
        self.status.showMessage("Face analysis complete.", 5000)

    def _face_analysis_failed(self, message: str) -> None:
        QMessageBox.warning(
            self,
            "Face analysis could not complete",
            message,
        )
        self.face_analysis.set_busy(False, message)
        self.status.showMessage("Face analysis failed.", 5000)

    def _face_analysis_thread_finished(self) -> None:
        self.face_analysis.set_busy(False)
        self.analysis_thread = None
        self.analysis_worker = None

    def start_face_matching(self, catalogue_path: str) -> None:
        if (
            not self.session.is_open
            or not self.session.project.analysis_file
        ):
            QMessageBox.information(
                self,
                "Face analysis required",
                "Run Face Analysis for the current project first.",
            )
            return
        if self.match_thread is not None:
            return

        analysis_path = (
            self.session.directory / self.session.project.analysis_file
        )
        catalogue = Path(catalogue_path)
        output_path = self.session.directory / "matches.json"

        if not catalogue.exists():
            QMessageBox.warning(
                self,
                "Catalogue missing",
                f"The selected catalogue does not exist:\n{catalogue}",
            )
            return

        thread = QThread(self)
        worker = FaceMatchingWorker(
            analysis_path,
            catalogue,
            output_path,
        )
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.progress.connect(
            lambda message: self.face_matcher.set_busy(True, message)
        )
        worker.completed.connect(self._face_matching_completed)
        worker.failed.connect(self._face_matching_failed)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._face_matching_thread_finished)

        self.match_thread = thread
        self.match_worker = worker
        self.face_matcher.set_busy(True, "Starting comparison…")
        self.status.showMessage("Calculating face matches…")
        thread.start()

    def _face_matching_completed(
        self,
        results,
        output_path: str,
    ) -> None:
        self.session.project.matches_file = str(
            Path(output_path).relative_to(self.session.directory)
        )
        self.project_service.save(
            self.session.project,
            self.session.directory,
        )
        self.face_matcher.show_results(
            results,
            Path(output_path),
        )
        self.status.showMessage("Face matching complete.", 5000)

    def _face_matching_failed(self, message: str) -> None:
        QMessageBox.warning(
            self,
            "Face matching could not complete",
            message,
        )
        self.face_matcher.set_busy(False, message)
        self.status.showMessage("Face matching failed.", 5000)

    def _face_matching_thread_finished(self) -> None:
        self.face_matcher.set_busy(False)
        self.match_thread = None
        self.match_worker = None

    def start_asset_scan(self, path: str) -> None:
        if self.scan_thread is not None:
            return

        root = Path(path)
        if not root.exists() or not root.is_dir():
            QMessageBox.warning(
                self,
                "Invalid folder",
                "Choose an existing folder.",
            )
            return

        self.asset_explorer.set_scanning(True)
        self.asset_explorer.update_progress(0, str(root))
        self.status.showMessage("Scanning assets…")

        thread = QThread(self)
        worker = AssetScanWorker(root)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.progress.connect(self.asset_explorer.update_progress)
        worker.completed.connect(self._asset_scan_completed)
        worker.failed.connect(self._asset_scan_failed)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._asset_scan_thread_finished)

        self.scan_thread = thread
        self.scan_worker = worker
        thread.start()

    def cancel_asset_scan(self) -> None:
        if self.scan_worker is not None:
            self.scan_worker.cancel()
        if self.analysis_thread is not None:
            self.analysis_thread.quit()
        if self.match_thread is not None:
            self.match_thread.quit()
            self.status.showMessage("Cancelling scan…")

    def _asset_scan_completed(self, result) -> None:
        try:
            count = self.asset_database.replace_root(
                result.root,
                result.records,
            )
        except OSError as exc:
            self._asset_scan_failed(str(exc))
            return

        self.asset_explorer.scan_finished(
            count,
            result.skipped_files,
            result.root,
        )
        self.status.showMessage(
            f"Indexed {count:,} files.",
            5000,
        )

    def _asset_scan_failed(self, message: str) -> None:
        QMessageBox.critical(
            self,
            "Asset scan failed",
            message,
        )
        self.status.showMessage("Asset scan failed.", 5000)

    def _asset_scan_thread_finished(self) -> None:
        self.asset_explorer.set_scanning(False)
        self.scan_thread = None
        self.scan_worker = None

    def configure_autosave(self) -> None:
        self.autosave_timer.stop()
        if self.config.autosave_enabled:
            self.autosave_timer.start(
                max(15, self.config.autosave_interval_seconds) * 1000
            )

    def autosave(self) -> None:
        if (
            self.config.autosave_enabled
            and self.session.is_open
            and self.session.dirty
        ):
            self.save_project(silent=True)

    def refresh_recent_projects(self) -> None:
        self.dashboard.set_recent_projects(
            self.recent_store.remove_missing()
        )

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
        if self.scan_worker is not None:
            self.scan_worker.cancel()
        if self.analysis_thread is not None:
            self.analysis_thread.quit()
        if self.match_thread is not None:
            self.match_thread.quit()
        if not self._confirm_discard_if_needed():
            event.ignore()
            return
        self.save_config()
        event.accept()

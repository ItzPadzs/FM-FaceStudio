from __future__ import annotations

import logging
from pathlib import Path
from PySide6.QtCore import QSize
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPushButton, QStackedWidget, QVBoxLayout, QWidget

from facestudio.ui.pages.about import AboutPage
from facestudio.ui.pages.base import PlaceholderPage
from facestudio.ui.pages.dashboard import DashboardPage
from facestudio.ui.pages.settings import SettingsPage
from facestudio.ui.theme import DARK_STYLESHEET, LIGHT_STYLESHEET
from facestudio.utils.config import AppConfig

LOGGER = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(self, config: AppConfig, config_path: Path) -> None:
        super().__init__()
        self.config = config
        self.config_path = config_path
        self.setWindowTitle("FM FaceStudio — Alpha 0.1")
        self.resize(1180, 760)
        self.setMinimumSize(QSize(920, 620))

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
        alpha = QLabel("ALPHA 0.1")
        alpha.setObjectName("Muted")
        side.addWidget(alpha)
        side.addSpacing(16)

        self.stack = QStackedWidget()
        settings = SettingsPage(config)
        settings.theme_changed.connect(self.apply_theme)
        settings.settings_changed.connect(self.save_config)

        pages = [
            ("Dashboard", DashboardPage()),
            ("Projects", PlaceholderPage("Projects", "Create and manage FaceStudio projects.", "Planned for Alpha 0.2.")),
            ("Face AI", PlaceholderPage("Face AI", "Analyse a player photo and produce a face descriptor.", "Prototype migration planned for Alpha 0.5.")),
            ("Asset Explorer", PlaceholderPage("Asset Explorer", "Index and browse FM26 appearance assets.", "Planned for Alpha 0.3.")),
            ("Mesh Viewer", PlaceholderPage("Mesh Viewer", "Inspect supported meshes in an interactive viewport.", "Planned for Alpha 0.3–0.4.")),
            ("Export", PlaceholderPage("Export Centre", "Build validated packages with backup and restore.", "Disabled until formats are fully validated.")),
            ("Settings", settings),
            ("About", AboutPage()),
        ]

        self.nav_buttons = []
        for index, (label, page) in enumerate(pages):
            self.stack.addWidget(page)
            button = QPushButton(label)
            button.setCheckable(True)
            button.clicked.connect(lambda checked=False, i=index: self.navigate(i))
            self.nav_buttons.append(button)
            side.addWidget(button)

        side.addStretch()
        footer = QLabel("Read-only research build")
        footer.setObjectName("Muted")
        side.addWidget(footer)

        outer.addWidget(sidebar)
        outer.addWidget(self.stack, 1)
        self.navigate(0)
        self.apply_theme(config.theme)
        LOGGER.info("Main window initialised")

    def navigate(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        for i, button in enumerate(self.nav_buttons):
            button.setChecked(i == index)

    def apply_theme(self, theme: str) -> None:
        self.config.theme = theme
        self.setStyleSheet(LIGHT_STYLESHEET if theme == "light" else DARK_STYLESHEET)

    def save_config(self) -> None:
        try:
            self.config.save(self.config_path)
        except OSError as exc:
            LOGGER.exception("Settings save failed")
            QMessageBox.warning(self, "Settings", f"Settings could not be saved:\n{exc}")

    def closeEvent(self, event) -> None:
        self.save_config()
        super().closeEvent(event)

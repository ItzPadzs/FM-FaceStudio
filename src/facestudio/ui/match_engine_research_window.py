from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QFrame, QPushButton, QVBoxLayout

from facestudio.ui.pack_test_install_window import PackTestInstallMainWindow
from facestudio.ui.pages.one_click_face_builder import OneClickFaceBuilderPage
from facestudio.utils.config import AppConfig


class MatchEngineResearchMainWindow(PackTestInstallMainWindow):
    """Alpha 6.2 shell exposing one clear face-building workflow."""

    def __init__(self, config: AppConfig, config_path: Path) -> None:
        super().__init__(config, config_path)

        # Keep the proven services and pages in the codebase, but remove their
        # separate navigation entries from the normal Alpha 6.2 experience.
        for button in self.nav_buttons:
            button.hide()

        self.one_click_face_builder_page = OneClickFaceBuilderPage()
        page_index = self.stack.count()
        self.stack.addWidget(self.one_click_face_builder_page)

        button = QPushButton("Build Face")
        button.setObjectName("NavButton")
        button.setCheckable(True)
        button.clicked.connect(lambda checked=False, index=page_index: self.navigate(index))
        self.nav_buttons.append(button)

        sidebar = self.findChild(QFrame, "Sidebar")
        layout = sidebar.layout() if sidebar is not None else None
        if isinstance(layout, QVBoxLayout):
            layout.insertWidget(max(0, layout.count() - 3), button)

        self.navigate(page_index)
        self.apply_theme(self.config.theme)

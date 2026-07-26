from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QFrame, QPushButton, QVBoxLayout

from facestudio.platform.service import PlatformService
from facestudio.ui.pages.platform import PlatformPage
from facestudio.ui.research_window import ResearchMainWindow
from facestudio.utils.config import AppConfig


class PlatformMainWindow(ResearchMainWindow):
    """Alpha 2.0 modular shell for the complete local research platform."""

    def __init__(self, config: AppConfig, config_path: Path) -> None:
        super().__init__(config, config_path)
        self.platform_service = PlatformService(
            config_path.parent,
            self.face_library_store,
            self.descriptor_preset_store,
        )
        self.platform_page = PlatformPage(self.platform_service)

        page_index = self.stack.count()
        self.stack.addWidget(self.platform_page)
        platform_button = QPushButton("FaceStudio Platform")
        platform_button.setObjectName("NavButton")
        platform_button.setCheckable(True)
        platform_button.clicked.connect(
            lambda checked=False, index=page_index: self.navigate(index)
        )
        self.nav_buttons.append(platform_button)

        sidebar = self.findChild(QFrame, "Sidebar")
        layout = sidebar.layout() if sidebar is not None else None
        if isinstance(layout, QVBoxLayout):
            layout.insertWidget(max(0, layout.count() - 3), platform_button)
        self.apply_theme(self.config.theme)

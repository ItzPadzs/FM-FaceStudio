from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QFrame, QPushButton, QVBoxLayout

from facestudio.research.suite import ResearchSuiteService
from facestudio.ui.pages.research_suite import ResearchSuitePage
from facestudio.ui.preset_window import PresetMainWindow
from facestudio.utils.config import AppConfig


class ResearchMainWindow(PresetMainWindow):
    """Alpha 1.0 shell combining analysis, library, presets and research tools."""

    def __init__(self, config: AppConfig, config_path: Path) -> None:
        super().__init__(config, config_path)
        self.research_service = ResearchSuiteService(
            config_path.parent,
            self.face_library_store,
            self.descriptor_preset_store,
        )
        self.research_suite = ResearchSuitePage(self.research_service)

        page_index = self.stack.count()
        self.stack.addWidget(self.research_suite)
        research_button = QPushButton("Research Suite")
        research_button.setObjectName("NavButton")
        research_button.setCheckable(True)
        research_button.clicked.connect(
            lambda checked=False, index=page_index: self.navigate(index)
        )
        self.nav_buttons.append(research_button)

        sidebar = self.findChild(QFrame, "Sidebar")
        layout = sidebar.layout() if sidebar is not None else None
        if isinstance(layout, QVBoxLayout):
            layout.insertWidget(max(0, layout.count() - 3), research_button)
        self.apply_theme(self.config.theme)

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QFrame, QPushButton, QVBoxLayout

from facestudio.match_engine_research.service import MatchEngineResearchService
from facestudio.ui.pack_test_install_window import PackTestInstallMainWindow
from facestudio.ui.pages.match_engine_research import MatchEngineResearchPage
from facestudio.utils.config import AppConfig


class MatchEngineResearchMainWindow(PackTestInstallMainWindow):
    """Alpha 4.0 shell adding read-only match-engine research tooling."""

    def __init__(self, config: AppConfig, config_path: Path) -> None:
        super().__init__(config, config_path)
        self.match_engine_research_service = MatchEngineResearchService()
        self.match_engine_research_page = MatchEngineResearchPage(self.match_engine_research_service)

        page_index = self.stack.count()
        self.stack.addWidget(self.match_engine_research_page)
        button = QPushButton("Match Engine Research")
        button.setObjectName("NavButton")
        button.setCheckable(True)
        button.clicked.connect(lambda checked=False, index=page_index: self.navigate(index))
        self.nav_buttons.append(button)

        sidebar = self.findChild(QFrame, "Sidebar")
        layout = sidebar.layout() if sidebar is not None else None
        if isinstance(layout, QVBoxLayout):
            layout.insertWidget(max(0, layout.count() - 3), button)
        self.apply_theme(self.config.theme)

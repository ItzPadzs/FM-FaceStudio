from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QFrame, QPushButton, QVBoxLayout

from facestudio.match_engine_research.service import MatchEngineResearchService
from facestudio.ui.pack_test_install_window import PackTestInstallMainWindow
from facestudio.ui.pages.match_engine_research import MatchEngineResearchPage
from facestudio.ui.pages.mesh_head_studio import MeshHeadStudioPage
from facestudio.ui.pages.photo_to_3d import PhotoTo3DPage
from facestudio.ui.pages.texture_studio import TextureStudioPage
from facestudio.utils.config import AppConfig


class MatchEngineResearchMainWindow(PackTestInstallMainWindow):
    """Alpha 6 shell combining all research and head-authoring workflows."""

    def __init__(self, config: AppConfig, config_path: Path) -> None:
        super().__init__(config, config_path)
        self.match_engine_research_service = MatchEngineResearchService()
        self.match_engine_research_page = MatchEngineResearchPage(self.match_engine_research_service)
        self.texture_studio_page = TextureStudioPage()
        self.photo_to_3d_page = PhotoTo3DPage()
        self.mesh_head_studio_page = MeshHeadStudioPage()

        sidebar = self.findChild(QFrame, "Sidebar")
        layout = sidebar.layout() if sidebar is not None else None

        for page, label in (
            (self.match_engine_research_page, "Match Engine Research"),
            (self.texture_studio_page, "Texture Studio"),
            (self.photo_to_3d_page, "2D Photo to Head"),
            (self.mesh_head_studio_page, "2D to 3D Mesh Studio"),
        ):
            page_index = self.stack.count()
            self.stack.addWidget(page)
            button = QPushButton(label)
            button.setObjectName("NavButton")
            button.setCheckable(True)
            button.clicked.connect(lambda checked=False, index=page_index: self.navigate(index))
            self.nav_buttons.append(button)
            if isinstance(layout, QVBoxLayout):
                layout.insertWidget(max(0, layout.count() - 3), button)

        self.apply_theme(self.config.theme)

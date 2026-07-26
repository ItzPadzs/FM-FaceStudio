from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QFrame, QPushButton, QVBoxLayout

from facestudio.graphics_pack.service import GraphicsPackService
from facestudio.ui.image_studio_window import ImageStudioMainWindow
from facestudio.ui.pages.graphics_pack import GraphicsPackPage
from facestudio.utils.config import AppConfig


class GraphicsPackMainWindow(ImageStudioMainWindow):
    """Alpha 3.0 shell adding standard user graphics-pack construction."""

    def __init__(self, config: AppConfig, config_path: Path) -> None:
        super().__init__(config, config_path)
        self.graphics_pack_service = GraphicsPackService(
            config_path.parent,
            self.image_studio_service,
        )
        self.graphics_pack_page = GraphicsPackPage(self.graphics_pack_service)

        page_index = self.stack.count()
        self.stack.addWidget(self.graphics_pack_page)
        pack_button = QPushButton("Graphics Pack Builder")
        pack_button.setObjectName("NavButton")
        pack_button.setCheckable(True)
        pack_button.clicked.connect(
            lambda checked=False, index=page_index: self.navigate(index)
        )
        self.nav_buttons.append(pack_button)

        sidebar = self.findChild(QFrame, "Sidebar")
        layout = sidebar.layout() if sidebar is not None else None
        if isinstance(layout, QVBoxLayout):
            layout.insertWidget(max(0, layout.count() - 3), pack_button)
        self.apply_theme(self.config.theme)

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QFrame, QPushButton, QVBoxLayout

from facestudio.image_studio.service import ImageStudioService
from facestudio.ui.pages.image_studio import ImageStudioPage
from facestudio.ui.platform_window import PlatformMainWindow
from facestudio.utils.config import AppConfig


class ImageStudioMainWindow(PlatformMainWindow):
    """Alpha 2.1 shell adding local, non-destructive image preparation."""

    def __init__(self, config: AppConfig, config_path: Path) -> None:
        super().__init__(config, config_path)
        self.image_studio_service = ImageStudioService(config_path.parent)
        self.image_studio_page = ImageStudioPage(self.image_studio_service)

        page_index = self.stack.count()
        self.stack.addWidget(self.image_studio_page)
        image_button = QPushButton("Image Studio")
        image_button.setObjectName("NavButton")
        image_button.setCheckable(True)
        image_button.clicked.connect(
            lambda checked=False, index=page_index: self.navigate(index)
        )
        self.nav_buttons.append(image_button)

        sidebar = self.findChild(QFrame, "Sidebar")
        layout = sidebar.layout() if sidebar is not None else None
        if isinstance(layout, QVBoxLayout):
            layout.insertWidget(max(0, layout.count() - 3), image_button)
        self.apply_theme(self.config.theme)

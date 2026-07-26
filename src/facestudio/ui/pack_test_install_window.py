from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QFrame, QPushButton, QVBoxLayout

from facestudio.pack_tools.service import PackTestInstallService
from facestudio.ui.graphics_pack_window import GraphicsPackMainWindow
from facestudio.ui.pages.pack_test_install import PackTestInstallPage
from facestudio.utils.config import AppConfig


class PackTestInstallMainWindow(GraphicsPackMainWindow):
    """Alpha 3.1 shell adding validation, dry-run installation and verification."""

    def __init__(self, config: AppConfig, config_path: Path) -> None:
        super().__init__(config, config_path)
        self.pack_test_install_service = PackTestInstallService(config_path.parent)
        self.pack_test_install_page = PackTestInstallPage(self.pack_test_install_service)

        page_index = self.stack.count()
        self.stack.addWidget(self.pack_test_install_page)
        button = QPushButton("Pack Test & Install")
        button.setObjectName("NavButton")
        button.setCheckable(True)
        button.clicked.connect(lambda checked=False, index=page_index: self.navigate(index))
        self.nav_buttons.append(button)

        sidebar = self.findChild(QFrame, "Sidebar")
        layout = sidebar.layout() if sidebar is not None else None
        if isinstance(layout, QVBoxLayout):
            layout.insertWidget(max(0, layout.count() - 3), button)
        self.apply_theme(self.config.theme)

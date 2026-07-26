from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout

from facestudio.ui.main_window import MainWindow
from facestudio.utils.config import AppConfig

APP_NAME = "FM FaceStudio"
APP_VERSION = "Alpha 0.8.0 Build 2"

_SHELL_BASE = """
QLabel {
    background: transparent;
}
QFrame#Sidebar {
    border-right-width: 1px;
}
QLabel#Brand {
    padding: 0;
    margin: 0;
}
QLabel#VersionLabel {
    font-size: 9pt;
    font-weight: 700;
    padding-bottom: 8px;
}
QLabel#SidebarCaption {
    font-size: 8pt;
    font-weight: 700;
    padding-top: 8px;
}
QLabel#ProjectSummary {
    border-radius: 9px;
    padding: 10px;
}
QPushButton#NavButton {
    min-height: 22px;
    border-radius: 9px;
    padding: 9px 13px;
}
QPushButton#NavButton:checked {
    font-weight: 700;
}
QStatusBar {
    min-height: 24px;
    padding-left: 8px;
}
"""

_DARK_SHELL = """
QLabel#VersionLabel { color: #6ea8ff; }
QLabel#SidebarCaption { color: #7f8998; }
QLabel#ProjectSummary {
    color: #b6bec9;
    background: #151920;
    border: 1px solid #2d3440;
}
"""

_LIGHT_SHELL = """
QLabel#VersionLabel { color: #2867b2; }
QLabel#SidebarCaption { color: #778291; }
QLabel#ProjectSummary {
    color: #566171;
    background: #f6f8fb;
    border: 1px solid #d9dfe7;
}
"""


class AlphaMainWindow(MainWindow):
    """Alpha 0.8 application shell layered over the validated workspace logic."""

    def __init__(self, config: AppConfig, config_path: Path) -> None:
        super().__init__(config, config_path)
        self._polish_alpha_shell()

    def apply_theme(self, theme: str) -> None:
        super().apply_theme(theme)
        shell_theme = _LIGHT_SHELL if theme == "light" else _DARK_SHELL
        self.setStyleSheet(self.styleSheet() + _SHELL_BASE + shell_theme)

    def _polish_alpha_shell(self) -> None:
        self.setWindowTitle(f"{APP_NAME} — {APP_VERSION}")
        self.resize(1360, 840)
        self.setMinimumSize(QSize(1080, 700))

        sidebar = self.findChild(QFrame, "Sidebar")
        if sidebar is None:
            return

        sidebar.setMinimumWidth(240)
        sidebar.setMaximumWidth(270)

        for label in sidebar.findChildren(QLabel):
            if label.text() == "FM FaceStudio":
                label.setText(APP_NAME)
            elif label.text() == "SPRINT 7":
                label.setText(APP_VERSION)
                label.setObjectName("VersionLabel")

        for button in sidebar.findChildren(QPushButton):
            button.setObjectName("NavButton")
            if button.text() == "Dashboard":
                button.setText("Home")

        self.project_label.setObjectName("ProjectSummary")
        self.project_label.setText(
            "No project open\nCreate or open a project to begin."
        )

        layout = sidebar.layout()
        if isinstance(layout, QVBoxLayout):
            caption = QLabel("CURRENT PROJECT")
            caption.setObjectName("SidebarCaption")
            layout.insertWidget(max(0, layout.count() - 1), caption)

        # Reapply after assigning the Alpha object names so Qt repolishes them.
        self.apply_theme(self.config.theme)
        self.status.showMessage(f"{APP_VERSION} ready.", 3500)

    def _set_session(self, project, directory: Path) -> None:
        super()._set_session(project, directory)
        self.setWindowTitle(f"{project.name} — {APP_NAME}")

    def mark_dirty(self) -> None:
        super().mark_dirty()
        if self.session.is_open:
            self.setWindowTitle(
                f"{self.session.project.name} * — {APP_NAME}"
            )

    def save_project(self, silent: bool = False) -> bool:
        saved = super().save_project(silent=silent)
        if saved and self.session.is_open:
            self.setWindowTitle(
                f"{self.session.project.name} — {APP_NAME}"
            )
        return saved

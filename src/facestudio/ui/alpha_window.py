from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout

from facestudio.ui.main_window import MainWindow
from facestudio.ui.widgets.toast_notification import ToastNotification
from facestudio.utils.config import AppConfig
from facestudio.version import APP_NAME, APP_VERSION

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
    padding: 11px;
    line-height: 1.25;
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
QFrame#ToastNotification {
    border-radius: 11px;
}
QLabel#ToastMessage {
    font-weight: 600;
}
QPushButton#ToastClose {
    border: none;
    background: transparent;
    padding: 0;
    text-align: center;
    font-size: 14pt;
}
"""

_DARK_SHELL = """
QLabel#VersionLabel { color: #6ea8ff; }
QLabel#SidebarCaption { color: #7f8998; }
QLabel#ProjectSummary {
    color: #c5ccd6;
    background: #151920;
    border: 1px solid #2d3440;
}
QFrame#ToastNotification {
    background: #202630;
    border: 1px solid #46556a;
}
QLabel#ToastMessage { color: #f4f7fb; }
QPushButton#ToastClose { color: #aeb8c6; }
QPushButton#ToastClose:hover { color: #ffffff; }
"""

_LIGHT_SHELL = """
QLabel#VersionLabel { color: #2867b2; }
QLabel#SidebarCaption { color: #778291; }
QLabel#ProjectSummary {
    color: #566171;
    background: #f6f8fb;
    border: 1px solid #d9dfe7;
}
QFrame#ToastNotification {
    background: #ffffff;
    border: 1px solid #b9c6d6;
}
QLabel#ToastMessage { color: #222a35; }
QPushButton#ToastClose { color: #6c7785; }
QPushButton#ToastClose:hover { color: #20242b; }
"""

_TOAST_KEYWORDS = (
    "saved",
    "created",
    "opened",
    "imported",
    "complete",
    "failed",
    "indexed",
    "cancelled",
    "could not",
)


class AlphaMainWindow(MainWindow):
    """Alpha 0.8 application shell layered over the validated workspace logic."""

    def __init__(self, config: AppConfig, config_path: Path) -> None:
        super().__init__(config, config_path)
        self.toast = ToastNotification(self.centralWidget())
        self.status.messageChanged.connect(self._status_message_changed)
        self._polish_alpha_shell()

    def apply_theme(self, theme: str) -> None:
        super().apply_theme(theme)
        shell_theme = _LIGHT_SHELL if theme == "light" else _DARK_SHELL
        self.setStyleSheet(self.styleSheet() + _SHELL_BASE + shell_theme)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        if hasattr(self, "toast"):
            self.toast.reposition()

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

        self.apply_theme(self.config.theme)
        self.status.showMessage(f"{APP_VERSION} ready.", 3500)

    def _status_message_changed(self, message: str) -> None:
        normalised = message.strip().lower()
        if normalised and any(word in normalised for word in _TOAST_KEYWORDS):
            self.toast.show_message(message)

    def _set_session(self, project, directory: Path) -> None:
        super()._set_session(project, directory)
        self.setWindowTitle(f"{project.name} — {APP_NAME}")
        self.project_label.setText(
            f"{project.name}\nReady • {directory.name}"
        )

    def mark_dirty(self) -> None:
        super().mark_dirty()
        if self.session.is_open:
            self.setWindowTitle(
                f"{self.session.project.name} * — {APP_NAME}"
            )
            self.project_label.setText(
                f"{self.session.project.name}\nUnsaved changes"
            )

    def save_project(self, silent: bool = False) -> bool:
        saved = super().save_project(silent=silent)
        if saved and self.session.is_open:
            self.setWindowTitle(
                f"{self.session.project.name} — {APP_NAME}"
            )
            self.project_label.setText(
                f"{self.session.project.name}\nSaved • {self.session.directory.name}"
            )
        return saved

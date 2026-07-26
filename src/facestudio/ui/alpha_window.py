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
QFrame#ActivityBanner {
    border-radius: 10px;
}
QLabel#ActivityMessage {
    font-weight: 600;
    padding: 2px;
}
QProgressBar#ActivityProgress {
    min-height: 8px;
    max-height: 8px;
    border-radius: 4px;
    text-visible: false;
}
QGroupBox#WorkspaceCard {
    font-weight: 700;
}
QLabel#PreviewSurface {
    border-radius: 10px;
    padding: 12px;
}
QLabel#MetricValue {
    font-weight: 700;
}
QPlainTextEdit#AnalysisDetails,
QTableWidget#ResultsTable {
    border-radius: 8px;
    padding: 4px;
}
QTableWidget#ResultsTable::item {
    padding: 6px;
}
QHeaderView::section {
    border: none;
    padding: 8px;
    font-weight: 700;
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
QFrame#ActivityBanner {
    background: #192331;
    border: 1px solid #31465f;
}
QFrame#ActivityBanner[busy="true"] {
    background: #1e2939;
    border-color: #4a86d4;
}
QLabel#ActivityMessage { color: #c9d8eb; }
QProgressBar#ActivityProgress {
    background: #111820;
    border: 1px solid #34465c;
}
QProgressBar#ActivityProgress::chunk { background: #4a86d4; }
QLabel#PreviewSurface {
    background: #12151a;
    border: 1px dashed #465062;
    color: #8993a2;
}
QLabel#MetricValue { color: #f5f8fc; }
QPlainTextEdit#AnalysisDetails,
QTableWidget#ResultsTable {
    background: #14181e;
    border: 1px solid #303642;
    alternate-background-color: #1a1f27;
    gridline-color: #2d3440;
}
QHeaderView::section {
    background: #202630;
    color: #dce4ef;
    border-bottom: 1px solid #3a4453;
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
QFrame#ToastNotification {
    background: #ffffff;
    border: 1px solid #b9c6d6;
}
QLabel#ToastMessage { color: #222a35; }
QPushButton#ToastClose { color: #6c7785; }
QPushButton#ToastClose:hover { color: #20242b; }
QFrame#ActivityBanner {
    background: #edf5ff;
    border: 1px solid #bfd5ee;
}
QFrame#ActivityBanner[busy="true"] {
    background: #e5f0fd;
    border-color: #78a6dc;
}
QLabel#ActivityMessage { color: #31506f; }
QProgressBar#ActivityProgress {
    background: #ffffff;
    border: 1px solid #b9cadc;
}
QProgressBar#ActivityProgress::chunk { background: #2f6fca; }
QLabel#PreviewSurface {
    background: #f8fafc;
    border: 1px dashed #b7c2d0;
    color: #778291;
}
QLabel#MetricValue { color: #202733; }
QPlainTextEdit#AnalysisDetails,
QTableWidget#ResultsTable {
    background: #ffffff;
    border: 1px solid #d9dfe7;
    alternate-background-color: #f5f8fc;
    gridline-color: #e1e6ed;
}
QHeaderView::section {
    background: #edf2f8;
    color: #2c3542;
    border-bottom: 1px solid #d3dbe5;
}
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

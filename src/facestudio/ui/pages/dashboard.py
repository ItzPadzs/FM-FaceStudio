from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from facestudio.fm.installation import detect_installation
from facestudio.projects.recent import RecentProject


class DashboardPage(QWidget):
    new_project_requested = Signal()
    open_project_requested = Signal()
    recent_project_requested = Signal(str)

    def __init__(self) -> None:
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 28, 30, 28)
        layout.setSpacing(14)

        title = QLabel("Dashboard")
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        subtitle = QLabel(
            "Create a new player project or continue where you left off."
        )
        subtitle.setObjectName("Muted")
        layout.addWidget(subtitle)

        actions = QGridLayout()
        new_button = QPushButton("＋  New Project")
        new_button.setObjectName("Primary")
        new_button.clicked.connect(self.new_project_requested.emit)
        open_button = QPushButton("Open Project")
        open_button.clicked.connect(self.open_project_requested.emit)
        actions.addWidget(new_button, 0, 0)
        actions.addWidget(open_button, 0, 1)
        layout.addLayout(actions)

        installation = detect_installation()
        install_text = str(installation.root) if installation else "Not detected automatically"

        status_grid = QGridLayout()
        cards = [
            ("FM26 installation", install_text),
            ("Current sprint", "Sprint 6 — Face Matcher"),
            ("Autosave", "Enabled"),
            ("Safety", "Read-only"),
        ]
        for index, (heading, value) in enumerate(cards):
            card = QGroupBox(heading)
            card_layout = QVBoxLayout(card)
            label = QLabel(value)
            label.setWordWrap(True)
            label.setObjectName("Muted")
            card_layout.addWidget(label)
            status_grid.addWidget(card, index // 2, index % 2)
        layout.addLayout(status_grid)

        recent_box = QGroupBox("Recent projects")
        recent_layout = QVBoxLayout(recent_box)
        self.recent_container = QWidget()
        self.recent_layout = QVBoxLayout(self.recent_container)
        self.recent_layout.setContentsMargins(0, 0, 0, 0)
        self.recent_layout.setSpacing(7)
        recent_layout.addWidget(self.recent_container)
        layout.addWidget(recent_box)
        layout.addStretch()

    def set_recent_projects(self, projects: list[RecentProject]) -> None:
        while self.recent_layout.count():
            item = self.recent_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        if not projects:
            empty = QLabel("No recent projects yet.")
            empty.setObjectName("Muted")
            self.recent_layout.addWidget(empty)
            return

        for project in projects:
            button = QPushButton(f"{project.name}\n{project.path}")
            button.setToolTip(project.path)
            button.clicked.connect(
                lambda checked=False, path=project.path:
                self.recent_project_requested.emit(path)
            )
            self.recent_layout.addWidget(button)

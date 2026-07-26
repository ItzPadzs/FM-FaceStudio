from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
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
        layout.setContentsMargins(36, 32, 36, 32)
        layout.setSpacing(20)

        eyebrow = QLabel("FM FACESTUDIO")
        eyebrow.setObjectName("Eyebrow")
        layout.addWidget(eyebrow)

        title = QLabel("Home")
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        subtitle = QLabel(
            "Build a player project, analyse a source photograph, and refine "
            "descriptor-based face matches from one focused workspace."
        )
        subtitle.setObjectName("PageSubtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        hero = QFrame()
        hero.setObjectName("HeroCard")
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(22, 20, 22, 20)
        hero_layout.setSpacing(12)

        hero_copy = QVBoxLayout()
        hero_title = QLabel("Start your next player")
        hero_title.setObjectName("SectionTitle")
        hero_copy.addWidget(hero_title)
        hero_text = QLabel(
            "Create a fresh FaceStudio project or continue an existing one."
        )
        hero_text.setObjectName("Muted")
        hero_text.setWordWrap(True)
        hero_copy.addWidget(hero_text)
        hero_layout.addLayout(hero_copy, 1)

        new_button = QPushButton("New Project")
        new_button.setObjectName("Primary")
        new_button.clicked.connect(self.new_project_requested.emit)
        hero_layout.addWidget(new_button)

        open_button = QPushButton("Open Project")
        open_button.setObjectName("Secondary")
        open_button.clicked.connect(self.open_project_requested.emit)
        hero_layout.addWidget(open_button)

        layout.addWidget(hero)

        installation = detect_installation()
        install_text = (
            str(installation.root)
            if installation
            else "Not detected automatically"
        )

        status_grid = QGridLayout()
        status_grid.setHorizontalSpacing(14)
        status_grid.setVerticalSpacing(14)
        cards = [
            ("FM26 installation", install_text),
            ("Version", "Alpha 0.8.0 Build 1"),
            ("Autosave", "Enabled"),
            ("Workspace safety", "Read-only game access"),
        ]
        for index, (heading, value) in enumerate(cards):
            card = QGroupBox(heading)
            card.setObjectName("StatusCard")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(16, 18, 16, 16)
            label = QLabel(value)
            label.setWordWrap(True)
            label.setObjectName("CardValue")
            card_layout.addWidget(label)
            status_grid.addWidget(card, index // 2, index % 2)

        layout.addLayout(status_grid)

        recent_box = QGroupBox("Recent projects")
        recent_box.setObjectName("RecentProjects")
        recent_layout = QVBoxLayout(recent_box)
        recent_layout.setContentsMargins(16, 20, 16, 16)
        self.recent_container = QWidget()
        self.recent_layout = QVBoxLayout(self.recent_container)
        self.recent_layout.setContentsMargins(0, 0, 0, 0)
        self.recent_layout.setSpacing(8)
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
            empty = QLabel(
                "No recent projects yet. Create a project to get started."
            )
            empty.setObjectName("Muted")
            self.recent_layout.addWidget(empty)
            return

        for project in projects:
            button = QPushButton(f"{project.name}\n{project.path}")
            button.setObjectName("RecentProject")
            button.setToolTip(project.path)
            button.clicked.connect(
                lambda checked=False, path=project.path:
                self.recent_project_requested.emit(path)
            )
            self.recent_layout.addWidget(button)

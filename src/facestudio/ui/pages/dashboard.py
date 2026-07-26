from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from facestudio.fm.installation import detect_installation
from facestudio.projects.recent import RecentProject
from facestudio.version import APP_NAME, APP_VERSION


class DashboardPage(QWidget):
    new_project_requested = Signal()
    open_project_requested = Signal()
    import_photo_requested = Signal()
    current_project_requested = Signal()
    recent_project_requested = Signal(str)

    def __init__(self) -> None:
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 30, 36, 30)
        layout.setSpacing(18)

        eyebrow = QLabel(APP_NAME.upper())
        eyebrow.setObjectName("Eyebrow")
        layout.addWidget(eyebrow)

        title = QLabel("Project Workspace")
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        subtitle = QLabel(
            "Start a player project, continue recent work and move directly into "
            "the next useful stage of the FaceStudio workflow."
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
        hero_copy.setSpacing(5)
        hero_title = QLabel("Create or open a player workspace")
        hero_title.setObjectName("SectionTitle")
        hero_copy.addWidget(hero_title)
        hero_text = QLabel(
            "Each project keeps its photograph, analysis, descriptor data and "
            "generated previews together in one portable folder."
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

        self.current_card = QFrame()
        self.current_card.setObjectName("CurrentProjectCard")
        current_layout = QHBoxLayout(self.current_card)
        current_layout.setContentsMargins(20, 18, 20, 18)
        current_layout.setSpacing(16)

        current_copy = QVBoxLayout()
        current_copy.setSpacing(5)
        current_caption = QLabel("CURRENT PROJECT")
        current_caption.setObjectName("Eyebrow")
        current_copy.addWidget(current_caption)
        self.current_name = QLabel("No project open")
        self.current_name.setObjectName("SectionTitle")
        current_copy.addWidget(self.current_name)
        self.current_path = QLabel("Create a project or open a recent workspace to begin.")
        self.current_path.setObjectName("Muted")
        self.current_path.setWordWrap(True)
        current_copy.addWidget(self.current_path)
        self.current_progress = QLabel("Photo not imported  •  Analysis not run")
        self.current_progress.setObjectName("ProjectProgress")
        self.current_progress.setWordWrap(True)
        current_copy.addWidget(self.current_progress)
        current_layout.addLayout(current_copy, 1)

        self.import_button = QPushButton("Import Photograph")
        self.import_button.setObjectName("Secondary")
        self.import_button.setEnabled(False)
        self.import_button.clicked.connect(self.import_photo_requested.emit)
        current_layout.addWidget(self.import_button)

        self.continue_button = QPushButton("Continue Project")
        self.continue_button.setObjectName("Primary")
        self.continue_button.setEnabled(False)
        self.continue_button.clicked.connect(self.current_project_requested.emit)
        current_layout.addWidget(self.continue_button)
        layout.addWidget(self.current_card)

        section_row = QHBoxLayout()
        recent_title = QLabel("Recent projects")
        recent_title.setObjectName("SectionTitle")
        section_row.addWidget(recent_title)
        section_row.addStretch()
        self.recent_summary = QLabel("No recent workspaces")
        self.recent_summary.setObjectName("Muted")
        section_row.addWidget(self.recent_summary)
        layout.addLayout(section_row)

        self.recent_container = QWidget()
        self.recent_layout = QGridLayout(self.recent_container)
        self.recent_layout.setContentsMargins(0, 0, 0, 0)
        self.recent_layout.setHorizontalSpacing(14)
        self.recent_layout.setVerticalSpacing(14)
        layout.addWidget(self.recent_container)

        installation = detect_installation()
        install_text = "FM26 detected" if installation else "FM26 path not configured"
        footer = QLabel(
            f"{APP_VERSION}  •  Autosave enabled  •  {install_text}  •  "
            "Read-only game access"
        )
        footer.setObjectName("Muted")
        footer.setWordWrap(True)
        layout.addWidget(footer)
        layout.addStretch()

    def set_current_project(
        self,
        name: str | None,
        path: str | None,
        source_photo: str | None = None,
        analysis_file: str | None = None,
        dirty: bool = False,
    ) -> None:
        active = bool(name and path)
        self.import_button.setEnabled(active)
        self.continue_button.setEnabled(active)

        if not active:
            self.current_name.setText("No project open")
            self.current_path.setText(
                "Create a project or open a recent workspace to begin."
            )
            self.current_progress.setText(
                "Photo not imported  •  Analysis not run"
            )
            return

        self.current_name.setText(f"{name}{'  •  Unsaved' if dirty else ''}")
        self.current_path.setText(str(path))
        photo_state = "Photograph ready" if source_photo else "Photo not imported"
        analysis_state = "Analysis ready" if analysis_file else "Analysis not run"
        self.current_progress.setText(f"{photo_state}  •  {analysis_state}")

    def set_recent_projects(self, projects: list[RecentProject]) -> None:
        while self.recent_layout.count():
            item = self.recent_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        visible_projects = projects[:6]
        self.recent_summary.setText(
            f"{len(projects)} workspace{'s' if len(projects) != 1 else ''}"
            if projects
            else "No recent workspaces"
        )

        if not visible_projects:
            empty = QFrame()
            empty.setObjectName("EmptyWorkspaceCard")
            empty_layout = QVBoxLayout(empty)
            empty_layout.setContentsMargins(20, 18, 20, 18)
            empty_title = QLabel("Your recent projects will appear here")
            empty_title.setObjectName("SectionTitle")
            empty_layout.addWidget(empty_title)
            empty_text = QLabel(
                "Create your first FaceStudio project to start building a reusable "
                "player workspace."
            )
            empty_text.setObjectName("Muted")
            empty_text.setWordWrap(True)
            empty_layout.addWidget(empty_text)
            self.recent_layout.addWidget(empty, 0, 0, 1, 2)
            return

        for index, project in enumerate(visible_projects):
            project_path = Path(project.path)
            card = QPushButton()
            card.setObjectName("ProjectWorkspaceButton")
            card.setToolTip(project.path)
            card.setText(
                f"{project.name}\n"
                f"{'Available' if project_path.exists() else 'Folder unavailable'}  •  "
                f"{project_path.name}\n"
                f"{project.path}"
            )
            card.clicked.connect(
                lambda checked=False, path=project.path: (
                    self.recent_project_requested.emit(path)
                )
            )
            self.recent_layout.addWidget(card, index // 2, index % 2)

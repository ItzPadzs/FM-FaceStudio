from __future__ import annotations

from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from facestudio.platform.service import PlatformService


class PlatformPage(QWidget):
    def __init__(self, service: PlatformService) -> None:
        super().__init__()
        self.service = service
        root = QVBoxLayout(self)
        heading = QLabel("FaceStudio Platform")
        heading.setObjectName("PageTitle")
        root.addWidget(heading)
        root.addWidget(QLabel(
            "Local research guidance, visual summaries, plugin validation, project metadata and modular workspace status."
        ))

        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 1)
        self.tabs.addTab(self._assistant_tab(), "Research Assistant")
        self.tabs.addTab(self._visualisation_tab(), "Visualisation")
        self.tabs.addTab(self._plugins_tab(), "Plugin SDK")
        self.tabs.addTab(self._projects_tab(), "Projects")
        self.tabs.addTab(self._modules_tab(), "Modules")
        self.refresh_all()

    def _assistant_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        info = QLabel(
            "Guidance is generated locally from transparent FaceStudio descriptor metadata; it does not generate faces."
        )
        info.setWordWrap(True)
        layout.addWidget(info)
        self.assistant_list = QListWidget()
        layout.addWidget(self.assistant_list, 1)
        button = QPushButton("Refresh guidance")
        button.clicked.connect(self.refresh_assistant)
        layout.addWidget(button)
        return page

    def _visualisation_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.visual_summary = QTextEdit()
        self.visual_summary.setReadOnly(True)
        layout.addWidget(self.visual_summary, 1)
        button = QPushButton("Refresh summaries")
        button.clicked.connect(self.refresh_visualisation)
        layout.addWidget(button)
        return page

    def _plugins_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel(
            "Place each local plugin in its own data-directory/plugins folder with a facestudio-plugin.json manifest. "
            "This preview validates metadata and never executes third-party code."
        ))
        self.plugin_table = QTableWidget(0, 4)
        self.plugin_table.setHorizontalHeaderLabels(["Name", "Version", "Type", "Status"])
        layout.addWidget(self.plugin_table, 1)
        button = QPushButton("Discover plugins")
        button.clicked.connect(self.refresh_plugins)
        layout.addWidget(button)
        return page

    def _projects_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        form_box = QGroupBox("New local research project")
        form = QFormLayout(form_box)
        self.project_name = QLineEdit()
        self.project_description = QLineEdit()
        form.addRow("Name", self.project_name)
        form.addRow("Description", self.project_description)
        add_button = QPushButton("Create project")
        add_button.clicked.connect(self.create_project)
        form.addRow(add_button)
        layout.addWidget(form_box)
        self.project_table = QTableWidget(0, 5)
        self.project_table.setHorizontalHeaderLabels(["Name", "Status", "Owner", "Reviewers", "Milestones"])
        layout.addWidget(self.project_table, 1)
        return page

    def _modules_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.module_table = QTableWidget(0, 2)
        self.module_table.setHorizontalHeaderLabels(["Module", "Status"])
        layout.addWidget(self.module_table)
        return page

    def refresh_all(self) -> None:
        self.refresh_assistant()
        self.refresh_visualisation()
        self.refresh_plugins()
        self.refresh_projects()
        self.refresh_modules()

    def refresh_assistant(self) -> None:
        self.assistant_list.clear()
        self.assistant_list.addItems(self.service.assistant_summary())

    def refresh_visualisation(self) -> None:
        data = self.service.visualisation_data()
        shapes = "\n".join(f"  {key}: {value}" for key, value in sorted(data["face_shapes"].items())) or "  No data"
        collections = "\n".join(f"  {key}: {value}" for key, value in sorted(data["collections"].items())) or "  No data"
        confidence = data["confidence_bands"]
        self.visual_summary.setPlainText(
            f"Average confidence: {data['average_confidence'] * 100:.1f}%\n\n"
            f"Confidence bands\n  High: {confidence['high']}\n  Medium: {confidence['medium']}\n  Low: {confidence['low']}\n\n"
            f"Face shapes\n{shapes}\n\nCollections\n{collections}"
        )

    def refresh_plugins(self) -> None:
        plugins = self.service.discover_plugins()
        self.plugin_table.setRowCount(len(plugins))
        for row, plugin in enumerate(plugins):
            for column, key in enumerate(("name", "version", "type", "status")):
                self.plugin_table.setItem(row, column, QTableWidgetItem(str(plugin.get(key, ""))))

    def create_project(self) -> None:
        self.service.add_project(self.project_name.text(), self.project_description.text())
        self.project_name.clear()
        self.project_description.clear()
        self.refresh_projects()

    def refresh_projects(self) -> None:
        projects = self.service.load_projects()
        self.project_table.setRowCount(len(projects))
        for row, project in enumerate(projects):
            values = [
                project.name,
                project.status,
                project.owner,
                ", ".join(project.reviewers),
                ", ".join(project.milestones),
            ]
            for column, value in enumerate(values):
                self.project_table.setItem(row, column, QTableWidgetItem(value))

    def refresh_modules(self) -> None:
        modules = self.service.module_registry()
        self.module_table.setRowCount(len(modules))
        for row, module in enumerate(modules):
            self.module_table.setItem(row, 0, QTableWidgetItem(module["module"]))
            self.module_table.setItem(row, 1, QTableWidgetItem(module["status"]))

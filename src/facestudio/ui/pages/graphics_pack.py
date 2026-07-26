from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from facestudio.graphics_pack.service import GraphicsPackEntry, GraphicsPackService


class GraphicsPackPage(QWidget):
    def __init__(self, service: GraphicsPackService) -> None:
        super().__init__()
        self.service = service
        self.entries: list[GraphicsPackEntry] = []

        root = QVBoxLayout(self)
        heading = QLabel("Graphics Pack Builder")
        heading.setObjectName("PageTitle")
        root.addWidget(heading)

        scope = QLabel(
            "Build standard PNG portrait folders and XML mappings from Image Studio records using user-supplied Football Manager unique IDs."
        )
        scope.setWordWrap(True)
        root.addWidget(scope)

        controls = QHBoxLayout()
        self.pack_name = QLineEdit("FaceStudio Facepack")
        self.pack_name.setPlaceholderText("Pack name")
        controls.addWidget(self.pack_name, 1)
        sync_button = QPushButton("Sync Image Studio")
        sync_button.clicked.connect(self.sync_library)
        controls.addWidget(sync_button)
        validate_button = QPushButton("Validate")
        validate_button.clicked.connect(self.validate_project)
        controls.addWidget(validate_button)
        build_button = QPushButton("Build Pack")
        build_button.clicked.connect(self.build_pack)
        controls.addWidget(build_button)
        root.addLayout(controls)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Include", "Image", "Football Manager Unique ID", "Status"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.itemChanged.connect(self.save_table_change)
        root.addWidget(self.table, 1)

        root.addWidget(QLabel("Validation and build log"))
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(180)
        root.addWidget(self.log)

        note = QLabel(
            "This workspace does not edit the Football Manager database, generate 3D heads, decode proprietary files or install anything automatically."
        )
        note.setWordWrap(True)
        root.addWidget(note)
        self.refresh()

    def refresh(self) -> None:
        self.entries = self.service.load_entries()
        self.table.blockSignals(True)
        self.table.setRowCount(len(self.entries))
        issues = self.service.validate(self.entries)
        issue_text = "\n".join(issues)
        for row, entry in enumerate(self.entries):
            include = QTableWidgetItem()
            include.setFlags(include.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            include.setCheckState(Qt.CheckState.Checked if entry.enabled else Qt.CheckState.Unchecked)
            include.setData(Qt.ItemDataRole.UserRole, entry.id)
            self.table.setItem(row, 0, include)

            name = QTableWidgetItem(entry.display_name)
            name.setFlags(name.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 1, name)

            unique_id = QTableWidgetItem(entry.unique_id)
            self.table.setItem(row, 2, unique_id)

            row_issues = [line for line in issues if line.startswith(f"{entry.display_name}:")]
            self.table.setItem(row, 3, QTableWidgetItem("Ready" if not row_issues else "; ".join(row_issues)))
        self.table.blockSignals(False)
        self.log.setPlainText(issue_text or f"Ready: {sum(1 for item in self.entries if item.enabled)} enabled entries.")

    def sync_library(self) -> None:
        added, removed = self.service.sync_from_image_library()
        self.refresh()
        self.log.append(f"Synced Image Studio: {added} added, {removed} removed.")

    def save_table_change(self, item: QTableWidgetItem) -> None:
        row = item.row()
        if row < 0 or row >= len(self.entries):
            return
        entry = self.entries[row]
        include_item = self.table.item(row, 0)
        id_item = self.table.item(row, 2)
        entry.enabled = include_item.checkState() == Qt.CheckState.Checked if include_item else True
        entry.unique_id = id_item.text().strip() if id_item else ""
        self.service.update_entry(entry)
        self.refresh()

    def validate_project(self) -> None:
        issues = self.service.validate()
        if issues:
            self.log.setPlainText("\n".join(issues))
            QMessageBox.warning(self, "Validation issues", f"Found {len(issues)} issue(s). See the build log.")
        else:
            enabled = sum(1 for item in self.service.load_entries() if item.enabled)
            self.log.setPlainText(f"Validation passed for {enabled} enabled portraits.")
            QMessageBox.information(self, "Validation passed", "The graphics pack project is ready to build.")

    def build_pack(self) -> None:
        destination = QFileDialog.getExistingDirectory(self, "Choose output folder")
        if not destination:
            return
        try:
            result = self.service.build_pack(Path(destination), self.pack_name.text())
        except (OSError, ValueError) as exc:
            self.log.setPlainText(str(exc))
            QMessageBox.critical(self, "Build failed", str(exc))
            return
        pack_dir = result["pack_dir"]
        count = result["count"]
        self.log.setPlainText(f"Built {count} portraits.\nOutput: {pack_dir}")
        QMessageBox.information(self, "Pack built", f"Built {count} portraits in:\n{pack_dir}")

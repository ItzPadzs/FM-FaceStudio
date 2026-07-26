from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QFileDialog, QFormLayout, QHBoxLayout, QInputDialog, QLabel, QLineEdit,
    QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QTabWidget,
    QTextEdit, QVBoxLayout, QWidget,
)

from facestudio.research.suite import ResearchSuiteService


class ResearchSuitePage(QWidget):
    def __init__(self, service: ResearchSuiteService) -> None:
        super().__init__()
        self.service = service
        layout = QVBoxLayout(self)
        title = QLabel("Research Suite")
        title.setObjectName("PageTitle")
        layout.addWidget(title)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        self.tabs.addTab(self._dashboard_tab(), "Dashboard")
        self.tabs.addTab(self._search_tab(), "Global Search")
        self.tabs.addTab(self._collections_tab(), "Collections")
        self.tabs.addTab(self._integrity_tab(), "Integrity")
        self.tabs.addTab(self._backup_tab(), "Backup Centre")
        self.tabs.addTab(self._reports_tab(), "Reports")
        self.refresh_all()

    def _dashboard_tab(self) -> QWidget:
        page = QWidget(); layout = QVBoxLayout(page)
        self.dashboard_text = QTextEdit(); self.dashboard_text.setReadOnly(True)
        refresh = QPushButton("Refresh dashboard"); refresh.clicked.connect(self.refresh_all)
        layout.addWidget(refresh); layout.addWidget(self.dashboard_text)
        return page

    def _search_tab(self) -> QWidget:
        page = QWidget(); layout = QVBoxLayout(page)
        row = QHBoxLayout(); self.search_input = QLineEdit(); self.search_input.setPlaceholderText("Search faces, presets, collections, tags and notes")
        button = QPushButton("Search"); button.clicked.connect(self.run_search)
        row.addWidget(self.search_input); row.addWidget(button); layout.addLayout(row)
        self.search_table = QTableWidget(0, 4); self.search_table.setHorizontalHeaderLabels(["Type", "Name", "Collection", "Detail"])
        layout.addWidget(self.search_table)
        return page

    def _collections_tab(self) -> QWidget:
        page = QWidget(); layout = QVBoxLayout(page)
        self.collections_text = QTextEdit(); self.collections_text.setReadOnly(True)
        button = QPushButton("Rename collection"); button.clicked.connect(self.rename_collection)
        layout.addWidget(button); layout.addWidget(self.collections_text)
        return page

    def _integrity_tab(self) -> QWidget:
        page = QWidget(); layout = QVBoxLayout(page)
        button = QPushButton("Run integrity check"); button.clicked.connect(self.refresh_integrity)
        self.integrity_table = QTableWidget(0, 3); self.integrity_table.setHorizontalHeaderLabels(["Severity", "Item", "Issue"])
        layout.addWidget(button); layout.addWidget(self.integrity_table)
        return page

    def _backup_tab(self) -> QWidget:
        page = QWidget(); layout = QVBoxLayout(page)
        create = QPushButton("Create backup"); create.clicked.connect(self.create_backup)
        restore = QPushButton("Restore backup"); restore.clicked.connect(self.restore_backup)
        self.backup_status = QLabel("Backups contain FaceStudio's transparent local JSON stores only.")
        layout.addWidget(create); layout.addWidget(restore); layout.addWidget(self.backup_status); layout.addStretch()
        return page

    def _reports_tab(self) -> QWidget:
        page = QWidget(); layout = QFormLayout(page)
        self.report_title = QLineEdit("FM FaceStudio Research Report")
        export = QPushButton("Export HTML report"); export.clicked.connect(self.export_report)
        layout.addRow("Report title", self.report_title); layout.addRow(export)
        return page

    def refresh_all(self) -> None:
        stats = self.service.statistics()
        shapes = "\n".join(f"  {name}: {count}" for name, count in stats["face_shapes"].items()) or "  No face data"
        tags = ", ".join(f"{name} ({count})" for name, count in stats["tags"].items()) or "No tags"
        self.dashboard_text.setPlainText(
            f"Faces: {stats['faces']}\nDescriptor presets: {stats['presets']}\nSaved comparisons: {stats['comparisons']}\n"
            f"Favourites: {stats['favourites']}\nAverage confidence: {stats['average_confidence']:.1%}\n\nFace shapes:\n{shapes}\n\nTop tags: {tags}"
        )
        collections = stats["collections"]
        self.collections_text.setPlainText("\n".join(f"{name}: {count} item(s)" for name, count in collections.items()) or "No collections yet.")
        self.refresh_integrity()

    def run_search(self) -> None:
        results = self.service.global_search(self.search_input.text())
        self.search_table.setRowCount(len(results))
        for row, result in enumerate(results):
            for column, key in enumerate(("type", "name", "collection", "detail")):
                self.search_table.setItem(row, column, QTableWidgetItem(str(result[key])))

    def refresh_integrity(self) -> None:
        issues = self.service.integrity_report()
        self.integrity_table.setRowCount(len(issues))
        for row, issue in enumerate(issues):
            for column, key in enumerate(("severity", "item", "issue")):
                self.integrity_table.setItem(row, column, QTableWidgetItem(str(issue[key])))

    def rename_collection(self) -> None:
        old_name, ok = QInputDialog.getText(self, "Rename collection", "Existing collection name")
        if not ok or not old_name.strip(): return
        new_name, ok = QInputDialog.getText(self, "Rename collection", "New collection name")
        if not ok or not new_name.strip(): return
        changed = self.service.rename_collection(old_name.strip(), new_name.strip())
        QMessageBox.information(self, "Collection updated", f"Updated {changed} item(s).")
        self.refresh_all()

    def create_backup(self) -> None:
        filename, _ = QFileDialog.getSaveFileName(self, "Create FaceStudio backup", str(self.service.backup_dir / "facestudio-backup.zip"), "ZIP archives (*.zip)")
        if not filename: return
        try:
            path = self.service.create_backup(Path(filename))
            self.backup_status.setText(f"Backup created: {path}")
        except Exception as exc:
            QMessageBox.critical(self, "Backup failed", str(exc))

    def restore_backup(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(self, "Restore FaceStudio backup", str(self.service.backup_dir), "ZIP archives (*.zip)")
        if not filename: return
        answer = QMessageBox.question(self, "Restore backup", "Restore this backup over the current local stores? A safety backup will be created first.")
        if answer != QMessageBox.StandardButton.Yes: return
        try:
            self.service.create_backup()
            self.service.restore_backup(Path(filename))
            self.backup_status.setText("Backup restored. Restart FaceStudio to reload all workspaces.")
            self.refresh_all()
        except Exception as exc:
            QMessageBox.critical(self, "Restore failed", str(exc))

    def export_report(self) -> None:
        filename, _ = QFileDialog.getSaveFileName(self, "Export research report", str(self.service.report_dir / "facestudio-report.html"), "HTML documents (*.html)")
        if not filename: return
        try:
            path = self.service.export_html_report(Path(filename), self.report_title.text().strip() or "FM FaceStudio Research Report")
            QMessageBox.information(self, "Report exported", f"Report saved to {path}")
        except Exception as exc:
            QMessageBox.critical(self, "Report failed", str(exc))

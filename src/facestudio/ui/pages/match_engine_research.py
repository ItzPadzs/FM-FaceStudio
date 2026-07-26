from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from facestudio.match_engine_research.service import MatchEngineResearchService, ScanReport


class MatchEngineResearchPage(QWidget):
    def __init__(self, service: MatchEngineResearchService) -> None:
        super().__init__()
        self.service = service
        self.report: ScanReport | None = None

        root = QVBoxLayout(self)
        title = QLabel("Match Engine Research")
        title.setObjectName("PageTitle")
        root.addWidget(title)

        summary = QLabel(
            "Start with evidence: scan a folder of files you are legally able to inspect, record file types, sizes, hashes and headers, then export a repeatable research report. FaceStudio does not alter the game or unpack proprietary archives."
        )
        summary.setWordWrap(True)
        root.addWidget(summary)

        path_row = QHBoxLayout()
        self.folder_path = QLineEdit()
        self.folder_path.setPlaceholderText("Choose a folder containing loose research files")
        browse = QPushButton("Browse")
        browse.clicked.connect(self.choose_folder)
        scan = QPushButton("Scan folder")
        scan.clicked.connect(self.scan_folder)
        export = QPushButton("Export report")
        export.clicked.connect(self.export_report)
        path_row.addWidget(self.folder_path, 1)
        path_row.addWidget(browse)
        path_row.addWidget(scan)
        path_row.addWidget(export)
        root.addLayout(path_row)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setPlainText(
            "First test:\n1. Make a small copy of files you want to study.\n2. Select that copied folder.\n3. Scan it.\n4. Export the JSON report.\n5. Change one controlled item and scan again for comparison."
        )
        root.addWidget(self.output, 1)

    def choose_folder(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Select a research folder")
        if selected:
            self.folder_path.setText(selected)

    def scan_folder(self) -> None:
        text = self.folder_path.text().strip()
        if not text:
            QMessageBox.warning(self, "Folder required", "Choose a folder first.")
            return
        try:
            self.report = self.service.scan(Path(text))
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Scan failed", str(exc))
            return

        category_counts: dict[str, int] = {}
        extension_counts: dict[str, int] = {}
        for record in self.report.records:
            category_counts[record.category] = category_counts.get(record.category, 0) + 1
            extension_counts[record.extension] = extension_counts.get(record.extension, 0) + 1

        lines = [
            "Read-only scan complete",
            "",
            f"Folder: {self.report.root}",
            f"Files recorded: {self.report.file_count}",
            f"Files skipped: {len(self.report.skipped)}",
            "",
            "Categories:",
            *(f"• {name}: {count}" for name, count in sorted(category_counts.items())),
            "",
            "Extensions:",
            *(f"• {name}: {count}" for name, count in sorted(extension_counts.items())),
        ]
        if self.report.skipped:
            lines.extend(["", "Skipped:", *(f"• {item}" for item in self.report.skipped)])
        lines.extend(["", "No files were changed."])
        self.output.setPlainText("\n".join(lines))

    def export_report(self) -> None:
        if self.report is None:
            QMessageBox.warning(self, "Nothing to export", "Scan a folder first.")
            return
        selected, _ = QFileDialog.getSaveFileName(
            self,
            "Export research report",
            "facestudio-match-engine-scan.json",
            "JSON files (*.json)",
        )
        if not selected:
            return
        try:
            destination = self.service.export_report(self.report, Path(selected))
        except OSError as exc:
            QMessageBox.critical(self, "Export failed", str(exc))
            return
        QMessageBox.information(self, "Report exported", f"Saved to:\n{destination}")

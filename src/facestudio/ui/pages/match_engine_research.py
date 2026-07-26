from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from facestudio.match_engine_research.head_explorer import HeadExplorerService, HeadLibrary, HeadRecord
from facestudio.match_engine_research.service import MatchEngineResearchService, ScanReport


class MatchEngineResearchPage(QWidget):
    def __init__(self, service: MatchEngineResearchService) -> None:
        super().__init__()
        self.service = service
        self.head_service = HeadExplorerService()
        self.report: ScanReport | None = None
        self.head_library: HeadLibrary | None = None

        root = QVBoxLayout(self)
        title = QLabel("Match Engine Research")
        title.setObjectName("PageTitle")
        root.addWidget(title)

        summary = QLabel(
            "Inspect copied research files in read-only mode. The Head Explorer groups observed FM26 loose head assets by player ID, reads plain-text CFG2 values and records binary SKIN evidence without claiming to decode its proprietary structure."
        )
        summary.setWordWrap(True)
        root.addWidget(summary)

        tabs = QTabWidget()
        tabs.addTab(self._build_head_explorer(), "FM26 Head Explorer")
        tabs.addTab(self._build_inventory(), "Generic File Inventory")
        root.addWidget(tabs, 1)

    def _build_head_explorer(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        path_row = QHBoxLayout()
        self.heads_path = QLineEdit()
        self.heads_path.setPlaceholderText("Choose a copied FM26 heads folder")
        browse = QPushButton("Browse")
        browse.clicked.connect(self.choose_heads_folder)
        load = QPushButton("Load heads")
        load.clicked.connect(self.load_heads)
        export = QPushButton("Export head report")
        export.clicked.connect(self.export_heads)
        path_row.addWidget(self.heads_path, 1)
        path_row.addWidget(browse)
        path_row.addWidget(load)
        path_row.addWidget(export)
        layout.addLayout(path_row)

        self.head_status = QLabel(
            "Use a separate copied folder where possible. FaceStudio will not edit PNG, CFG2, SKIN or JSON files."
        )
        self.head_status.setWordWrap(True)
        layout.addWidget(self.head_status)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.player_list = QListWidget()
        self.player_list.currentItemChanged.connect(self.show_player)
        splitter.addWidget(self.player_list)

        detail = QWidget()
        detail_layout = QVBoxLayout(detail)
        self.preview = QLabel("No player selected")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumSize(280, 280)
        self.preview.setMaximumHeight(420)
        self.preview.setScaledContents(False)
        detail_layout.addWidget(self.preview)
        self.head_output = QTextEdit()
        self.head_output.setReadOnly(True)
        detail_layout.addWidget(self.head_output, 1)
        splitter.addWidget(detail)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        layout.addWidget(splitter, 1)
        return page

    def _build_inventory(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
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
        layout.addLayout(path_row)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setPlainText(
            "This inventory records paths, sizes, hashes and headers. It does not unpack archives or modify files."
        )
        layout.addWidget(self.output, 1)
        return page

    def choose_heads_folder(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Select a copied FM26 heads folder")
        if selected:
            self.heads_path.setText(selected)

    def load_heads(self) -> None:
        text = self.heads_path.text().strip()
        if not text:
            QMessageBox.warning(self, "Folder required", "Choose a heads folder first.")
            return
        try:
            self.head_library = self.head_service.load(Path(text))
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Head scan failed", str(exc))
            return

        self.player_list.clear()
        for index, record in enumerate(self.head_library.records):
            item = QListWidgetItem(f"{record.player_name}  [{record.player_id}]  • {record.available_assets} assets")
            item.setData(Qt.ItemDataRole.UserRole, index)
            self.player_list.addItem(item)

        named = sum(record.player_name != "Unknown player" for record in self.head_library.records)
        self.head_status.setText(
            f"Loaded {len(self.head_library.records)} player records; {named} names resolved; "
            f"{len(self.head_library.warnings)} warnings. No files were changed."
        )
        if self.head_library.records:
            self.player_list.setCurrentRow(0)
        else:
            self.preview.setText("No matching head assets found")
            self.head_output.setPlainText("Expected files named with a numeric player ID and .png, .cfg2 or .skin extension.")

    def show_player(self, current: QListWidgetItem | None, previous: QListWidgetItem | None = None) -> None:
        del previous
        if current is None or self.head_library is None:
            return
        index = current.data(Qt.ItemDataRole.UserRole)
        if not isinstance(index, int) or not 0 <= index < len(self.head_library.records):
            return
        record = self.head_library.records[index]
        self._show_preview(record)
        self.head_output.setPlainText(self._format_head_record(record))

    def _show_preview(self, record: HeadRecord) -> None:
        if self.head_library is None or record.face_png is None:
            self.preview.setPixmap(QPixmap())
            self.preview.setText("No face PNG")
            return
        path = Path(self.head_library.root) / record.face_png
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            self.preview.setPixmap(QPixmap())
            self.preview.setText("PNG could not be displayed")
            return
        self.preview.setText("")
        self.preview.setPixmap(
            pixmap.scaled(
                self.preview.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    @staticmethod
    def _format_head_record(record: HeadRecord) -> str:
        lines = [
            f"Player: {record.player_name}",
            f"Football Manager ID: {record.player_id}",
            "",
            "Observed loose assets:",
            f"• Face PNG: {record.face_png or 'Missing'}",
            f"• CFG2: {record.config_cfg2 or 'Missing'}",
            f"• SKIN: {record.skin_file or 'Missing'}",
            f"• Hair PNG: {record.hair_png or 'Missing'}",
            f"• Hair 2 PNG: {record.hair2_png or 'Missing'}",
            f"• Hair SKIN: {record.hair_skin or 'Missing'}",
        ]
        if record.cfg2_comments or record.cfg2_values:
            lines.extend(["", "CFG2 — plain-text evidence:"])
            lines.extend(f"• Comment: {comment}" for comment in record.cfg2_comments)
            lines.extend(f"• {key} = {value}" for key, value in record.cfg2_values.items())
        if record.skin_summary is not None:
            summary = record.skin_summary
            lines.extend(
                [
                    "",
                    "SKIN — binary evidence only:",
                    f"• Size: {summary.size_bytes:,} bytes",
                    f"• SHA-256: {summary.sha256}",
                    f"• First 64 bytes: {summary.header_hex}",
                    "• First little-endian 32-bit values: " + ", ".join(str(value) for value in summary.little_endian_u32),
                    "",
                    "FaceStudio has not decoded what these binary fields mean.",
                ]
            )
        return "\n".join(lines)

    def export_heads(self) -> None:
        if self.head_library is None:
            QMessageBox.warning(self, "Nothing to export", "Load a heads folder first.")
            return
        selected, _ = QFileDialog.getSaveFileName(
            self,
            "Export FM26 head report",
            "facestudio-fm26-head-library.json",
            "JSON files (*.json)",
        )
        if not selected:
            return
        try:
            destination = self.head_service.export_library(self.head_library, Path(selected))
        except OSError as exc:
            QMessageBox.critical(self, "Export failed", str(exc))
            return
        QMessageBox.information(self, "Head report exported", f"Saved to:\n{destination}")

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

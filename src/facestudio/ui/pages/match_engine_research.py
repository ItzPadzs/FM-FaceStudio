from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIntValidator, QPixmap
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
from facestudio.match_engine_research.texture_builder import PhotoTextureBuilder


class MatchEngineResearchPage(QWidget):
    def __init__(self, service: MatchEngineResearchService) -> None:
        super().__init__()
        self.service = service
        self.head_service = HeadExplorerService()
        self.texture_builder = PhotoTextureBuilder()
        self.report: ScanReport | None = None
        self.head_library: HeadLibrary | None = None
        self.selected_record: HeadRecord | None = None
        self.photo_source: Path | None = None

        root = QVBoxLayout(self)
        title = QLabel("Match Engine Research")
        title.setObjectName("PageTitle")
        root.addWidget(title)
        summary = QLabel(
            "Research FM26 loose head assets by Football Manager unique ID. Inspect PNG, CFG2 and SKIN evidence, then create a non-destructive photo-on-template UV texture prototype for controlled testing."
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

        id_row = QHBoxLayout()
        self.unique_id = QLineEdit()
        self.unique_id.setPlaceholderText("Enter Football Manager unique ID")
        self.unique_id.setValidator(QIntValidator(0, 2_147_483_647, self))
        self.unique_id.returnPressed.connect(self.find_unique_id)
        find_button = QPushButton("Find unique ID")
        find_button.clicked.connect(self.find_unique_id)
        id_row.addWidget(QLabel("Unique ID:"))
        id_row.addWidget(self.unique_id, 1)
        id_row.addWidget(find_button)
        layout.addLayout(id_row)

        texture_row = QHBoxLayout()
        self.photo_path = QLineEdit()
        self.photo_path.setReadOnly(True)
        self.photo_path.setPlaceholderText("Choose a clear front-facing photograph")
        choose_photo = QPushButton("Choose photo")
        choose_photo.clicked.connect(self.choose_photo)
        build_texture = QPushButton("Create texture prototype")
        build_texture.clicked.connect(self.build_texture)
        texture_row.addWidget(self.photo_path, 1)
        texture_row.addWidget(choose_photo)
        texture_row.addWidget(build_texture)
        layout.addLayout(texture_row)

        self.head_status = QLabel(
            "Files are read-only. Generated textures are saved separately and never replace the selected FM26 source texture automatically."
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
        self.output.setPlainText("This inventory records paths, sizes, hashes and headers. It does not unpack archives or modify files.")
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
            item = QListWidgetItem(f"{record.player_id}  • {record.player_name}  • {record.available_assets} assets")
            item.setData(Qt.ItemDataRole.UserRole, index)
            self.player_list.addItem(item)
        named = sum(record.player_name != "Unknown player" for record in self.head_library.records)
        self.head_status.setText(
            f"Loaded {len(self.head_library.records)} unique IDs; {named} optional names resolved; "
            f"{len(self.head_library.warnings)} warnings. No files were changed."
        )
        if self.head_library.records:
            self.player_list.setCurrentRow(0)
        else:
            self.preview.setText("No matching head assets found")
            self.head_output.setPlainText("Expected files named with a numeric player ID and .png, .cfg2 or .skin extension.")

    def find_unique_id(self) -> None:
        player_id = self.unique_id.text().strip()
        if not player_id:
            QMessageBox.warning(self, "Unique ID required", "Enter a numeric Football Manager unique ID.")
            return
        if self.head_library is None:
            QMessageBox.warning(self, "Load heads first", "Load the heads folder before searching by unique ID.")
            return
        for row, record in enumerate(self.head_library.records):
            if record.player_id == player_id:
                self.player_list.setCurrentRow(row)
                self.player_list.scrollToItem(self.player_list.item(row))
                return
        QMessageBox.information(self, "Unique ID not found", f"No loose head assets were found for {player_id}.")

    def choose_photo(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(
            self,
            "Choose a front-facing photograph",
            "",
            "Images (*.png *.jpg *.jpeg *.webp *.bmp)",
        )
        if selected:
            self.photo_source = Path(selected)
            self.photo_path.setText(selected)

    def build_texture(self) -> None:
        if self.head_library is None or self.selected_record is None:
            QMessageBox.warning(self, "Player required", "Load the heads folder and select a unique ID first.")
            return
        if self.selected_record.face_png is None:
            QMessageBox.warning(self, "Template missing", "The selected unique ID has no face PNG to use as a UV template.")
            return
        if self.photo_source is None:
            QMessageBox.warning(self, "Photo required", "Choose a clear front-facing photograph first.")
            return
        selected, _ = QFileDialog.getSaveFileName(
            self,
            "Save texture prototype",
            f"{self.selected_record.player_id}-texture-prototype.png",
            "PNG files (*.png)",
        )
        if not selected:
            return
        template = Path(self.head_library.root) / self.selected_record.face_png
        try:
            result = self.texture_builder.build(
                self.selected_record.player_id,
                self.photo_source,
                template,
                Path(selected),
            )
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Texture build failed", str(exc))
            return
        QMessageBox.information(
            self,
            "Texture prototype created",
            f"Saved to:\n{result.destination}\n\nThis is an early centre-face UV composite, not a proven final match-engine texture. The original FM26 files were not changed.",
        )

    def show_player(self, current: QListWidgetItem | None, previous: QListWidgetItem | None = None) -> None:
        del previous
        if current is None or self.head_library is None:
            return
        index = current.data(Qt.ItemDataRole.UserRole)
        if not isinstance(index, int) or not 0 <= index < len(self.head_library.records):
            return
        record = self.head_library.records[index]
        self.selected_record = record
        self.unique_id.setText(record.player_id)
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
        self.preview.setPixmap(pixmap.scaled(self.preview.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    @staticmethod
    def _format_head_record(record: HeadRecord) -> str:
        lines = [
            f"Football Manager unique ID: {record.player_id}",
            f"Optional name: {record.player_name}",
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
            lines.extend([
                "",
                "SKIN — binary evidence only:",
                f"• Size: {summary.size_bytes:,} bytes",
                f"• SHA-256: {summary.sha256}",
                f"• First 64 bytes: {summary.header_hex}",
                "• First little-endian 32-bit values: " + ", ".join(str(value) for value in summary.little_endian_u32),
                "",
                "FaceStudio has not decoded what these binary fields mean.",
            ])
        lines.extend([
            "",
            "Photo texture prototype:",
            "• Uses this ID's face PNG only as an observed UV template.",
            "• Blends a centre-cropped front photo into the central face region.",
            "• Does not yet perform landmark detection, side projection or automatic skin-tone correction.",
        ])
        return "\n".join(lines)

    def export_heads(self) -> None:
        if self.head_library is None:
            QMessageBox.warning(self, "Nothing to export", "Load a heads folder first.")
            return
        selected, _ = QFileDialog.getSaveFileName(self, "Export FM26 head report", "facestudio-fm26-head-library.json", "JSON files (*.json)")
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
            "Read-only scan complete", "", f"Folder: {self.report.root}", f"Files recorded: {self.report.file_count}",
            f"Files skipped: {len(self.report.skipped)}", "", "Categories:",
            *(f"• {name}: {count}" for name, count in sorted(category_counts.items())), "", "Extensions:",
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
        selected, _ = QFileDialog.getSaveFileName(self, "Export research report", "facestudio-match-engine-scan.json", "JSON files (*.json)")
        if not selected:
            return
        try:
            destination = self.service.export_report(self.report, Path(selected))
        except OSError as exc:
            QMessageBox.critical(self, "Export failed", str(exc))
            return
        QMessageBox.information(self, "Report exported", f"Saved to:\n{destination}")

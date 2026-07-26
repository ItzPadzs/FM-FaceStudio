from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from facestudio.assets.database import AssetDatabase
from facestudio.ui.widgets.activity_banner import ActivityBanner
from facestudio.ui.widgets.page_header import PageHeader


def readable_size(value: int) -> str:
    size = float(value)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{value} B"


class AssetExplorerPage(QWidget):
    scan_requested = Signal(str)
    cancel_requested = Signal()
    asset_open_requested = Signal(str)

    def __init__(self, database: AssetDatabase) -> None:
        super().__init__()
        self.database = database
        self._result_paths: list[str] = []
        self._result_rows: list[object] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(16)

        self.scan_button = QPushButton("Scan folder")
        self.scan_button.setObjectName("Primary")
        self.scan_button.clicked.connect(self._request_scan)
        self.browse_button = QPushButton("Choose folder…")
        self.browse_button.setObjectName("Secondary")
        self.browse_button.clicked.connect(self._browse)
        self.cancel_button = QPushButton("Cancel scan")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_requested.emit)

        layout.addWidget(
            PageHeader(
                "Read-only asset research",
                "Asset Explorer",
                "Index file paths and metadata without modifying or claiming to decode "
                "Football Manager game assets. Search, inspect and open supported files "
                "in the Mesh Explorer from one focused workspace.",
                [self.browse_button, self.scan_button, self.cancel_button],
            )
        )

        self.activity = ActivityBanner("Choose a folder to scan or search the existing index.")
        layout.addWidget(self.activity)

        scan_box = QGroupBox("Indexed location")
        scan_box.setObjectName("WorkspaceCard")
        scan_layout = QHBoxLayout(scan_box)
        scan_layout.setContentsMargins(16, 20, 16, 16)
        self.root_path = QLineEdit()
        self.root_path.setPlaceholderText(
            "Football Manager installation or another read-only test folder"
        )
        scan_layout.addWidget(self.root_path, 1)
        layout.addWidget(scan_box)

        filter_box = QGroupBox("Search and filters")
        filter_box.setObjectName("WorkspaceCard")
        filter_layout = QHBoxLayout(filter_box)
        filter_layout.setContentsMargins(16, 20, 16, 16)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search filename or relative path…")
        self.type_filter = QComboBox()
        self.type_filter.addItem("All types", "")
        self.extension_filter = QComboBox()
        self.extension_filter.addItem("All extensions", "")
        clear_button = QPushButton("Clear")
        clear_button.clicked.connect(self._clear_filters)
        filter_layout.addWidget(self.search_edit, 2)
        filter_layout.addWidget(self.type_filter, 1)
        filter_layout.addWidget(self.extension_filter, 1)
        filter_layout.addWidget(clear_button)
        layout.addWidget(filter_box)

        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(250)
        self._search_timer.timeout.connect(self.refresh_results)
        self.search_edit.textChanged.connect(lambda: self._search_timer.start())
        self.type_filter.currentIndexChanged.connect(self.refresh_results)
        self.extension_filter.currentIndexChanged.connect(self.refresh_results)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        results_box = QGroupBox("Indexed assets")
        results_box.setObjectName("WorkspaceCard")
        results_layout = QVBoxLayout(results_box)
        results_layout.setContentsMargins(12, 18, 12, 12)
        self.summary = QLabel("No indexed assets.")
        self.summary.setObjectName("Muted")
        results_layout.addWidget(self.summary)

        self.table = QTableWidget(0, 6)
        self.table.setObjectName("ResultsTable")
        self.table.setHorizontalHeaderLabels(
            ["Type", "Filename", "Extension", "Size", "Modified", "Relative path"]
        )
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.verticalHeader().setVisible(False)
        self.table.itemSelectionChanged.connect(self._show_selection)
        self.table.cellDoubleClicked.connect(self._open_selected_asset)
        header = self.table.horizontalHeader()
        for index in range(5):
            header.setSectionResizeMode(index, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        results_layout.addWidget(self.table)
        splitter.addWidget(results_box)

        details_box = QGroupBox("Asset details")
        details_box.setObjectName("WorkspaceCard")
        details_layout = QVBoxLayout(details_box)
        details_layout.setContentsMargins(16, 20, 16, 16)

        self.preview = QLabel("Select an indexed asset")
        self.preview.setObjectName("PreviewSurface")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumSize(280, 220)
        details_layout.addWidget(self.preview)

        details_form = QFormLayout()
        details_form.setHorizontalSpacing(14)
        details_form.setVerticalSpacing(9)
        self.detail_name = QLabel("—")
        self.detail_type = QLabel("—")
        self.detail_size = QLabel("—")
        self.detail_modified = QLabel("—")
        self.detail_path = QLabel("—")
        self.detail_path.setWordWrap(True)
        for label in (
            self.detail_name,
            self.detail_type,
            self.detail_size,
            self.detail_modified,
        ):
            label.setObjectName("MetricValue")
        details_form.addRow("Filename", self.detail_name)
        details_form.addRow("Classification", self.detail_type)
        details_form.addRow("Size", self.detail_size)
        details_form.addRow("Modified", self.detail_modified)
        details_form.addRow("Full path", self.detail_path)
        details_layout.addLayout(details_form)

        self.open_button = QPushButton("Open in Mesh Explorer")
        self.open_button.setObjectName("Primary")
        self.open_button.setEnabled(False)
        self.open_button.clicked.connect(lambda: self._open_selected_asset(-1, -1))
        details_layout.addWidget(self.open_button)
        details_layout.addStretch()
        splitter.addWidget(details_box)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([900, 340])
        layout.addWidget(splitter, 1)

        self.refresh_filters()
        self.refresh_results()

    def _clear_filters(self) -> None:
        self.search_edit.clear()
        self.type_filter.setCurrentIndex(0)
        self.extension_filter.setCurrentIndex(0)
        self.refresh_results()

    def _selected_path(self) -> str | None:
        selected = self.table.selectionModel().selectedRows()
        if not selected:
            return None
        row = selected[0].row()
        return self._result_paths[row] if 0 <= row < len(self._result_paths) else None

    def _open_selected_asset(self, row: int, column: int) -> None:
        path = self._selected_path()
        if path is None and 0 <= row < len(self._result_paths):
            path = self._result_paths[row]
        if path:
            self.asset_open_requested.emit(path)

    def _show_selection(self) -> None:
        selected = self.table.selectionModel().selectedRows()
        if not selected:
            self.open_button.setEnabled(False)
            return
        row_index = selected[0].row()
        if not 0 <= row_index < len(self._result_rows):
            return
        row = self._result_rows[row_index]
        path = Path(self._result_paths[row_index])
        self.detail_name.setText(str(row["filename"]))
        self.detail_type.setText(f'{row["asset_type"]} • {row["extension"] or "no extension"}')
        self.detail_size.setText(readable_size(int(row["size_bytes"])))
        self.detail_modified.setText(
            datetime.fromtimestamp(float(row["modified_time"])).strftime("%d %b %Y, %H:%M")
        )
        self.detail_path.setText(str(path))
        self.open_button.setEnabled(True)

        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp", ".webp"}:
            pixmap = QPixmap(str(path))
            if not pixmap.isNull():
                self.preview.setPixmap(
                    pixmap.scaled(
                        self.preview.size(),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
                return
        self.preview.setPixmap(QPixmap())
        self.preview.setText(f"{path.suffix.upper() or 'FILE'}\nPreview unavailable")

    def _browse(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Choose a folder to scan")
        if directory:
            self.root_path.setText(directory)
            self.activity.set_state("Folder selected. Start the read-only scan when ready.")

    def _request_scan(self) -> None:
        path = self.root_path.text().strip()
        if not path:
            QMessageBox.information(self, "Choose a folder", "Select a folder before starting the scan.")
            return
        self.scan_requested.emit(path)

    def set_scanning(self, scanning: bool) -> None:
        self.scan_button.setEnabled(not scanning)
        self.browse_button.setEnabled(not scanning)
        self.cancel_button.setEnabled(scanning)
        self.root_path.setEnabled(not scanning)
        self.activity.set_state(
            "Scanning file metadata… The selected folder remains read-only." if scanning
            else "Scan stopped. Search the current index or choose another folder.",
            scanning,
        )

    def update_progress(self, count: int, current_path: str) -> None:
        self.activity.set_state(f"Scanned {count:,} files… {current_path}", True)

    def scan_finished(self, indexed_count: int, skipped_count: int, root: Path) -> None:
        self.activity.set_state(
            f"Indexed {indexed_count:,} files from {root}. Skipped {skipped_count:,} unreadable files."
        )
        self.refresh_filters()
        self.refresh_results()

    def refresh_filters(self) -> None:
        current_type = self.type_filter.currentData()
        current_extension = self.extension_filter.currentData()
        self.type_filter.blockSignals(True)
        self.type_filter.clear()
        self.type_filter.addItem("All types", "")
        for asset_type, count in self.database.counts_by_type().items():
            self.type_filter.addItem(f"{asset_type} ({count:,})", asset_type)
        self.type_filter.setCurrentIndex(max(0, self.type_filter.findData(current_type)))
        self.type_filter.blockSignals(False)

        self.extension_filter.blockSignals(True)
        self.extension_filter.clear()
        self.extension_filter.addItem("All extensions", "")
        for extension in self.database.extensions():
            self.extension_filter.addItem(extension, extension)
        self.extension_filter.setCurrentIndex(
            max(0, self.extension_filter.findData(current_extension))
        )
        self.extension_filter.blockSignals(False)

    def refresh_results(self) -> None:
        rows = self.database.search(
            query=self.search_edit.text(),
            asset_type=str(self.type_filter.currentData() or ""),
            extension=str(self.extension_filter.currentData() or ""),
            limit=5000,
        )
        total = self.database.total_count()
        self.summary.setText(
            f"Showing {len(rows):,} of {total:,} indexed files • maximum 5,000 results"
        )
        self._result_rows = list(rows)
        self._result_paths = [
            str(Path(str(row["root_path"])) / str(row["relative_path"])) for row in rows
        ]

        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            values = [
                str(row["asset_type"]),
                str(row["filename"]),
                str(row["extension"]),
                readable_size(int(row["size_bytes"])),
                datetime.fromtimestamp(float(row["modified_time"])).strftime("%Y-%m-%d %H:%M"),
                str(row["relative_path"]),
            ]
            for column_index, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column_index == 3:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(row_index, column_index, item)
        self.table.setSortingEnabled(True)
        self.open_button.setEnabled(False)
        self.preview.setPixmap(QPixmap())
        self.preview.setText("Select an indexed asset")

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, Signal
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
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from facestudio.assets.database import AssetDatabase


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

    def __init__(self, database: AssetDatabase) -> None:
        super().__init__()
        self.database = database

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(12)

        title = QLabel("Asset Explorer")
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        notice = QLabel(
            "Read-only scanner. It records file paths and metadata only; "
            "it does not modify or decode game files."
        )
        notice.setObjectName("Muted")
        notice.setWordWrap(True)
        layout.addWidget(notice)

        scanner_box = QGroupBox("Scan folder")
        scanner_layout = QHBoxLayout(scanner_box)
        self.root_path = QLineEdit()
        self.root_path.setPlaceholderText(
            "Choose the Football Manager installation or another test folder"
        )
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._browse)
        self.scan_button = QPushButton("Scan")
        self.scan_button.setObjectName("Primary")
        self.scan_button.clicked.connect(self._request_scan)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_requested.emit)
        scanner_layout.addWidget(self.root_path, 1)
        scanner_layout.addWidget(browse)
        scanner_layout.addWidget(self.scan_button)
        scanner_layout.addWidget(self.cancel_button)
        layout.addWidget(scanner_box)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        self.scan_status = QLabel("")
        self.scan_status.setObjectName("Muted")
        self.scan_status.setWordWrap(True)
        layout.addWidget(self.scan_status)

        filters = QGroupBox("Search and filters")
        filter_layout = QHBoxLayout(filters)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search filename or path…")
        self.type_filter = QComboBox()
        self.type_filter.addItem("All types", "")
        self.extension_filter = QComboBox()
        self.extension_filter.addItem("All extensions", "")
        refresh = QPushButton("Search")
        refresh.clicked.connect(self.refresh_results)
        self.search_edit.returnPressed.connect(self.refresh_results)
        self.type_filter.currentIndexChanged.connect(self.refresh_results)
        self.extension_filter.currentIndexChanged.connect(self.refresh_results)
        filter_layout.addWidget(self.search_edit, 2)
        filter_layout.addWidget(self.type_filter, 1)
        filter_layout.addWidget(self.extension_filter, 1)
        filter_layout.addWidget(refresh)
        layout.addWidget(filters)

        self.summary = QLabel("No indexed assets.")
        self.summary.setObjectName("Muted")
        layout.addWidget(self.summary)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["Type", "Filename", "Extension", "Size", "Modified", "Relative path"]
        )
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table, 1)

        self.refresh_filters()
        self.refresh_results()

    def _browse(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self,
            "Choose a folder to scan",
        )
        if directory:
            self.root_path.setText(directory)

    def _request_scan(self) -> None:
        path = self.root_path.text().strip()
        if not path:
            QMessageBox.information(
                self,
                "Choose a folder",
                "Select a folder before starting the scan.",
            )
            return
        self.scan_requested.emit(path)

    def set_scanning(self, scanning: bool) -> None:
        self.scan_button.setEnabled(not scanning)
        self.cancel_button.setEnabled(scanning)
        self.root_path.setEnabled(not scanning)
        self.progress.setVisible(scanning)

    def update_progress(self, count: int, current_path: str) -> None:
        self.scan_status.setText(
            f"Scanned {count:,} files…\n{current_path}"
        )

    def scan_finished(
        self,
        indexed_count: int,
        skipped_count: int,
        root: Path,
    ) -> None:
        self.scan_status.setText(
            f"Indexed {indexed_count:,} files from {root}. "
            f"Skipped {skipped_count:,} unreadable files."
        )
        self.refresh_filters()
        self.refresh_results()

    def refresh_filters(self) -> None:
        current_type = self.type_filter.currentData()
        current_extension = self.extension_filter.currentData()

        counts = self.database.counts_by_type()
        self.type_filter.blockSignals(True)
        self.type_filter.clear()
        self.type_filter.addItem("All types", "")
        for asset_type, count in counts.items():
            self.type_filter.addItem(f"{asset_type} ({count:,})", asset_type)
        index = self.type_filter.findData(current_type)
        self.type_filter.setCurrentIndex(max(0, index))
        self.type_filter.blockSignals(False)

        self.extension_filter.blockSignals(True)
        self.extension_filter.clear()
        self.extension_filter.addItem("All extensions", "")
        for extension in self.database.extensions():
            self.extension_filter.addItem(extension, extension)
        index = self.extension_filter.findData(current_extension)
        self.extension_filter.setCurrentIndex(max(0, index))
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
            f"Showing {len(rows):,} of {total:,} indexed files. "
            "Results are limited to 5,000 rows."
        )

        self.table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            values = [
                str(row["asset_type"]),
                str(row["filename"]),
                str(row["extension"]),
                readable_size(int(row["size_bytes"])),
                datetime.fromtimestamp(
                    float(row["modified_time"])
                ).strftime("%Y-%m-%d %H:%M"),
                str(row["relative_path"]),
            ]
            for column_index, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column_index == 3:
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight
                        | Qt.AlignmentFlag.AlignVCenter
                    )
                self.table.setItem(row_index, column_index, item)

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from facestudio.library.store import FaceLibraryRecord, FaceLibraryStore
from facestudio.ui.widgets.activity_banner import ActivityBanner
from facestudio.ui.widgets.page_header import PageHeader


class FaceLibraryPage(QWidget):
    add_current_requested = Signal()
    open_project_requested = Signal(str)

    def __init__(self, store: FaceLibraryStore) -> None:
        super().__init__()
        self.store = store
        self.records: list[FaceLibraryRecord] = []
        self.filtered: list[FaceLibraryRecord] = []
        self.current_record: FaceLibraryRecord | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(16)

        add_button = QPushButton("Add current analysis")
        add_button.setObjectName("Primary")
        add_button.clicked.connect(self.add_current_requested.emit)
        refresh_button = QPushButton("Refresh")
        refresh_button.setObjectName("Secondary")
        refresh_button.clicked.connect(self.refresh)
        layout.addWidget(PageHeader(
            "Reusable face research",
            "Face Library",
            "Store analysed project faces, search by name, tags, collection or face shape, and revisit the original project without repeating analysis.",
            [refresh_button, add_button],
        ))

        self.activity = ActivityBanner("Add an analysed project to begin building your reusable face library.")
        layout.addWidget(self.activity)

        filters = QGroupBox("Search and filters")
        filters.setObjectName("WorkspaceCard")
        filter_layout = QHBoxLayout(filters)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search name, tags, collection or notes…")
        self.shape_filter = QComboBox()
        self.shape_filter.addItem("All face shapes", "")
        self.collection_filter = QComboBox()
        self.collection_filter.addItem("All collections", "")
        self.favourites_only = QCheckBox("Favourites only")
        clear_button = QPushButton("Clear")
        clear_button.clicked.connect(self._clear_filters)
        filter_layout.addWidget(self.search, 2)
        filter_layout.addWidget(self.shape_filter, 1)
        filter_layout.addWidget(self.collection_filter, 1)
        filter_layout.addWidget(self.favourites_only)
        filter_layout.addWidget(clear_button)
        layout.addWidget(filters)

        self.search.textChanged.connect(self.apply_filters)
        self.shape_filter.currentIndexChanged.connect(self.apply_filters)
        self.collection_filter.currentIndexChanged.connect(self.apply_filters)
        self.favourites_only.toggled.connect(self.apply_filters)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        list_box = QGroupBox("Library faces")
        list_box.setObjectName("WorkspaceCard")
        list_layout = QVBoxLayout(list_box)
        self.summary = QLabel("No saved faces.")
        self.summary.setObjectName("Muted")
        list_layout.addWidget(self.summary)
        self.table = QTableWidget(0, 6)
        self.table.setObjectName("ResultsTable")
        self.table.setHorizontalHeaderLabels(["★", "Name", "Shape", "Confidence", "Collection", "Tags"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.itemSelectionChanged.connect(self._show_selection)
        list_layout.addWidget(self.table)
        splitter.addWidget(list_box)

        details = QGroupBox("Face details")
        details.setObjectName("WorkspaceCard")
        details_layout = QVBoxLayout(details)
        self.preview = QLabel("Select a saved face")
        self.preview.setObjectName("PreviewSurface")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumSize(300, 260)
        details_layout.addWidget(self.preview)

        form = QFormLayout()
        self.name_edit = QLineEdit()
        self.collection_edit = QLineEdit()
        self.tags_edit = QLineEdit()
        self.shape_label = QLabel("—")
        self.confidence_label = QLabel("—")
        self.project_label = QLabel("—")
        self.project_label.setWordWrap(True)
        self.favourite_edit = QCheckBox("Favourite")
        self.notes_edit = QPlainTextEdit()
        self.notes_edit.setPlaceholderText("Research notes…")
        self.notes_edit.setMaximumHeight(120)
        form.addRow("Name", self.name_edit)
        form.addRow("Face shape", self.shape_label)
        form.addRow("Confidence", self.confidence_label)
        form.addRow("Collection", self.collection_edit)
        form.addRow("Tags", self.tags_edit)
        form.addRow("Project", self.project_label)
        form.addRow("", self.favourite_edit)
        form.addRow("Notes", self.notes_edit)
        details_layout.addLayout(form)

        actions = QHBoxLayout()
        self.save_button = QPushButton("Save details")
        self.save_button.setObjectName("Primary")
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self._save_details)
        self.open_button = QPushButton("Open project")
        self.open_button.setEnabled(False)
        self.open_button.clicked.connect(self._open_project)
        self.remove_button = QPushButton("Remove")
        self.remove_button.setEnabled(False)
        self.remove_button.clicked.connect(self._remove_record)
        actions.addWidget(self.save_button)
        actions.addWidget(self.open_button)
        actions.addWidget(self.remove_button)
        details_layout.addLayout(actions)
        splitter.addWidget(details)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([780, 440])
        layout.addWidget(splitter, 1)
        self.refresh()

    def refresh(self) -> None:
        self.records = self.store.load()
        shapes = sorted({item.face_shape for item in self.records if item.face_shape})
        collections = sorted({item.collection for item in self.records if item.collection})
        self._reset_combo(self.shape_filter, "All face shapes", shapes)
        self._reset_combo(self.collection_filter, "All collections", collections)
        self.apply_filters()
        self.activity.set_state(
            f"Library ready with {len(self.records)} saved face{'s' if len(self.records) != 1 else ''}."
            if self.records else "Add an analysed project to begin building your reusable face library."
        )

    def _reset_combo(self, combo: QComboBox, label: str, values: list[str]) -> None:
        current = combo.currentData()
        combo.blockSignals(True)
        combo.clear()
        combo.addItem(label, "")
        for value in values:
            combo.addItem(value, value)
        index = combo.findData(current)
        combo.setCurrentIndex(max(0, index))
        combo.blockSignals(False)

    def _clear_filters(self) -> None:
        self.search.clear()
        self.shape_filter.setCurrentIndex(0)
        self.collection_filter.setCurrentIndex(0)
        self.favourites_only.setChecked(False)

    def apply_filters(self) -> None:
        query = self.search.text().strip().lower()
        shape = str(self.shape_filter.currentData() or "")
        collection = str(self.collection_filter.currentData() or "")
        self.filtered = []
        for record in self.records:
            haystack = " ".join([record.name, record.collection, " ".join(record.tags), record.notes]).lower()
            if query and query not in haystack:
                continue
            if shape and record.face_shape != shape:
                continue
            if collection and record.collection != collection:
                continue
            if self.favourites_only.isChecked() and not record.favourite:
                continue
            self.filtered.append(record)
        self.table.setRowCount(len(self.filtered))
        for row, record in enumerate(self.filtered):
            values = ["★" if record.favourite else "", record.name, record.face_shape.title(), f"{record.confidence:.1%}", record.collection, ", ".join(record.tags)]
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(value))
        self.table.resizeColumnsToContents()
        self.summary.setText(f"Showing {len(self.filtered)} of {len(self.records)} saved faces.")

    def _show_selection(self) -> None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        row = rows[0].row()
        if not 0 <= row < len(self.filtered):
            return
        record = self.filtered[row]
        self.current_record = record
        self.name_edit.setText(record.name)
        self.shape_label.setText(record.face_shape.title())
        self.confidence_label.setText(f"{record.confidence:.1%}")
        self.collection_edit.setText(record.collection)
        self.tags_edit.setText(", ".join(record.tags))
        self.project_label.setText(record.project_path)
        self.favourite_edit.setChecked(record.favourite)
        self.notes_edit.setPlainText(record.notes)
        self.save_button.setEnabled(True)
        self.open_button.setEnabled(Path(record.project_path).exists())
        self.remove_button.setEnabled(True)
        image_path = Path(record.preview_path or record.source_photo)
        pixmap = QPixmap(str(image_path)) if image_path.exists() else QPixmap()
        if pixmap.isNull():
            self.preview.setPixmap(QPixmap())
            self.preview.setText("Preview unavailable")
        else:
            self.preview.setPixmap(pixmap.scaled(self.preview.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def _save_details(self) -> None:
        if self.current_record is None:
            return
        self.current_record.name = self.name_edit.text().strip() or self.current_record.name
        self.current_record.collection = self.collection_edit.text().strip() or "Unsorted"
        self.current_record.tags = [value.strip() for value in self.tags_edit.text().split(",") if value.strip()]
        self.current_record.notes = self.notes_edit.toPlainText().strip()
        self.current_record.favourite = self.favourite_edit.isChecked()
        self.store.update(self.current_record)
        self.refresh()
        self.activity.set_state(f"Saved library details for {self.current_record.name}.")

    def _open_project(self) -> None:
        if self.current_record:
            self.open_project_requested.emit(self.current_record.project_path)

    def _remove_record(self) -> None:
        if self.current_record is None:
            return
        answer = QMessageBox.question(self, "Remove library face", f"Remove {self.current_record.name} from the library? The project files will not be deleted.")
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.store.remove(self.current_record.id)
        self.current_record = None
        self.refresh()

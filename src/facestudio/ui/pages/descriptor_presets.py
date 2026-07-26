from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QFileDialog, QFormLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPlainTextEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from facestudio.library.store import FaceLibraryStore
from facestudio.presets.library import DescriptorPreset, DescriptorPresetLibrary, descriptor_similarity
from facestudio.ui.widgets.activity_banner import ActivityBanner
from facestudio.ui.widgets.page_header import PageHeader


class DescriptorPresetsPage(QWidget):
    def __init__(self, store: DescriptorPresetLibrary, face_store: FaceLibraryStore) -> None:
        super().__init__()
        self.store = store
        self.face_store = face_store
        self.presets: list[DescriptorPreset] = []
        self.filtered: list[DescriptorPreset] = []
        self.current: DescriptorPreset | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(16)

        add_button = QPushButton("Add from Face Library")
        add_button.setObjectName("Primary")
        add_button.clicked.connect(self.add_from_library)
        import_button = QPushButton("Import preset…")
        import_button.clicked.connect(self.import_preset)
        layout.addWidget(PageHeader(
            "Reusable descriptor research",
            "Descriptor Presets",
            "Save FaceStudio descriptor profiles, organise them into collections and compare selected presets with a transparent component breakdown.",
            [import_button, add_button],
        ))
        self.activity = ActivityBanner("Add a Face Library record or import a FaceStudio preset to begin.")
        layout.addWidget(self.activity)

        filters = QGroupBox("Search and filters")
        filters.setObjectName("WorkspaceCard")
        filter_layout = QHBoxLayout(filters)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search name, collection, tags or source…")
        self.collection_filter = QComboBox()
        self.collection_filter.addItem("All collections", "")
        self.shape_filter = QComboBox()
        self.shape_filter.addItem("All face shapes", "")
        self.favourites_only = QCheckBox("Favourites only")
        filter_layout.addWidget(self.search, 2)
        filter_layout.addWidget(self.collection_filter)
        filter_layout.addWidget(self.shape_filter)
        filter_layout.addWidget(self.favourites_only)
        layout.addWidget(filters)

        self.table = QTableWidget(0, 7)
        self.table.setObjectName("ResultsTable")
        self.table.setHorizontalHeaderLabels(["Compare", "★", "Name", "Shape", "Confidence", "Collection", "Tags"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.itemSelectionChanged.connect(self.show_selection)
        layout.addWidget(self.table, 2)

        lower = QHBoxLayout()
        details = QGroupBox("Preset details")
        details.setObjectName("WorkspaceCard")
        form = QFormLayout(details)
        self.name_edit = QLineEdit()
        self.collection_edit = QLineEdit()
        self.tags_edit = QLineEdit()
        self.favourite_edit = QCheckBox("Favourite")
        self.source_label = QLabel("—")
        self.shape_label = QLabel("—")
        self.confidence_label = QLabel("—")
        self.notes_edit = QPlainTextEdit()
        self.notes_edit.setMaximumHeight(90)
        form.addRow("Name", self.name_edit)
        form.addRow("Collection", self.collection_edit)
        form.addRow("Tags", self.tags_edit)
        form.addRow("Source", self.source_label)
        form.addRow("Face shape", self.shape_label)
        form.addRow("Confidence", self.confidence_label)
        form.addRow("Status", self.favourite_edit)
        form.addRow("Notes", self.notes_edit)
        actions = QHBoxLayout()
        save = QPushButton("Save changes")
        save.setObjectName("Primary")
        save.clicked.connect(self.save_current)
        export = QPushButton("Export…")
        export.clicked.connect(self.export_current)
        remove = QPushButton("Remove")
        remove.clicked.connect(self.remove_current)
        actions.addWidget(save)
        actions.addWidget(export)
        actions.addWidget(remove)
        form.addRow(actions)
        lower.addWidget(details, 1)

        comparison = QGroupBox("Comparison set")
        comparison.setObjectName("WorkspaceCard")
        comparison_layout = QVBoxLayout(comparison)
        self.comparison_summary = QLabel("Tick two or more presets in the Compare column.")
        self.comparison_summary.setWordWrap(True)
        comparison_layout.addWidget(self.comparison_summary)
        compare = QPushButton("Compare selected")
        compare.setObjectName("Primary")
        compare.clicked.connect(self.compare_selected)
        comparison_layout.addWidget(compare)
        self.breakdown = QTableWidget(0, 2)
        self.breakdown.setObjectName("ResultsTable")
        self.breakdown.setHorizontalHeaderLabels(["Component", "Similarity"])
        self.breakdown.horizontalHeader().setStretchLastSection(True)
        self.breakdown.verticalHeader().setVisible(False)
        comparison_layout.addWidget(self.breakdown)
        self.history = QLabel("No comparison history yet.")
        self.history.setWordWrap(True)
        comparison_layout.addWidget(self.history)
        lower.addWidget(comparison, 1)
        layout.addLayout(lower, 2)

        self.search.textChanged.connect(self.apply_filters)
        self.collection_filter.currentIndexChanged.connect(self.apply_filters)
        self.shape_filter.currentIndexChanged.connect(self.apply_filters)
        self.favourites_only.toggled.connect(self.apply_filters)
        self.refresh()

    def refresh(self) -> None:
        self.presets = self.store.load()
        collections = sorted({item.collection for item in self.presets if item.collection})
        shapes = sorted({str(item.descriptor.get("face_shape", "undetermined")) for item in self.presets})
        self._reset_combo(self.collection_filter, "All collections", collections)
        self._reset_combo(self.shape_filter, "All face shapes", shapes)
        self.apply_filters()
        history = self.store.load_history()
        if history:
            latest = history[0]
            self.history.setText(f"Latest: {', '.join(latest.get('presets', []))} — {float(latest.get('similarity', 0)):.1%}")

    def _reset_combo(self, combo: QComboBox, label: str, values: list[str]) -> None:
        selected = combo.currentData()
        combo.blockSignals(True)
        combo.clear()
        combo.addItem(label, "")
        for value in values:
            combo.addItem(value, value)
        index = combo.findData(selected)
        combo.setCurrentIndex(max(0, index))
        combo.blockSignals(False)

    def apply_filters(self, *args) -> None:
        query = self.search.text().strip().lower()
        collection = str(self.collection_filter.currentData() or "")
        shape = str(self.shape_filter.currentData() or "")
        self.filtered = []
        for preset in self.presets:
            haystack = " ".join([preset.name, preset.collection, preset.source_name, preset.notes, *preset.tags]).lower()
            if query and query not in haystack:
                continue
            if collection and preset.collection != collection:
                continue
            if shape and str(preset.descriptor.get("face_shape", "")) != shape:
                continue
            if self.favourites_only.isChecked() and not preset.favourite:
                continue
            self.filtered.append(preset)
        self.table.setRowCount(len(self.filtered))
        for row, preset in enumerate(self.filtered):
            check = QTableWidgetItem()
            check.setCheckState(0)
            check.setData(256, preset.id)
            values = [check, QTableWidgetItem("★" if preset.favourite else ""), QTableWidgetItem(preset.name),
                      QTableWidgetItem(str(preset.descriptor.get("face_shape", "undetermined"))),
                      QTableWidgetItem(f"{preset.confidence:.1%}"), QTableWidgetItem(preset.collection),
                      QTableWidgetItem(", ".join(preset.tags))]
            for column, item in enumerate(values):
                self.table.setItem(row, column, item)
        self.activity.set_state(f"{len(self.filtered)} of {len(self.presets)} presets shown.")

    def show_selection(self) -> None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self.filtered):
            return
        self.current = self.filtered[row]
        self.name_edit.setText(self.current.name)
        self.collection_edit.setText(self.current.collection)
        self.tags_edit.setText(", ".join(self.current.tags))
        self.favourite_edit.setChecked(self.current.favourite)
        self.source_label.setText(self.current.source_name or "Imported preset")
        self.shape_label.setText(str(self.current.descriptor.get("face_shape", "undetermined")))
        self.confidence_label.setText(f"{self.current.confidence:.1%}")
        self.notes_edit.setPlainText(self.current.notes)

    def add_from_library(self) -> None:
        records = self.face_store.load()
        usable = [item for item in records if item.measurements]
        if not usable:
            QMessageBox.information(self, "No library faces", "Add analysed faces to the Face Library first.")
            return
        names = [item.name for item in usable]
        from PySide6.QtWidgets import QInputDialog
        name, accepted = QInputDialog.getItem(self, "Add descriptor preset", "Face Library record:", names, 0, False)
        if not accepted:
            return
        record = usable[names.index(name)]
        descriptor = dict(record.measurements)
        descriptor["face_shape"] = record.face_shape
        tags = sorted(set(record.tags + (["high-confidence"] if record.confidence >= 0.85 else [])))
        preset = DescriptorPreset(str(uuid4()), record.name, descriptor, record.id, record.name, record.confidence,
                                  record.collection, tags, record.favourite, "Created from Face Library.",
                                  datetime.now(timezone.utc).isoformat(timespec="seconds"))
        self.store.upsert(preset)
        self.refresh()

    def save_current(self) -> None:
        if self.current is None:
            return
        self.current.name = self.name_edit.text().strip() or self.current.name
        self.current.collection = self.collection_edit.text().strip() or "Unsorted"
        self.current.tags = sorted({value.strip() for value in self.tags_edit.text().split(",") if value.strip()})
        self.current.favourite = self.favourite_edit.isChecked()
        self.current.notes = self.notes_edit.toPlainText().strip()
        self.store.upsert(self.current)
        self.refresh()

    def import_preset(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(self, "Import FaceStudio preset", "", "FaceStudio descriptor (*.json)")
        if not filename:
            return
        try:
            preset = self.store.import_file(Path(filename))
        except (OSError, ValueError, TypeError) as exc:
            QMessageBox.critical(self, "Unable to import preset", str(exc))
            return
        self.activity.set_state(f"Imported {preset.name}.")
        self.refresh()

    def export_current(self) -> None:
        if self.current is None:
            return
        filename, _ = QFileDialog.getSaveFileName(self, "Export FaceStudio preset", f"{self.current.name}.json", "FaceStudio descriptor (*.json)")
        if filename:
            self.store.export_file(self.current, Path(filename))
            self.activity.set_state(f"Exported {self.current.name}.")

    def remove_current(self) -> None:
        if self.current is None:
            return
        self.store.remove(self.current.id)
        self.current = None
        self.refresh()

    def compare_selected(self) -> None:
        selected: list[DescriptorPreset] = []
        for row, preset in enumerate(self.filtered):
            item = self.table.item(row, 0)
            if item is not None and item.checkState() == 2:
                selected.append(preset)
        if len(selected) < 2:
            QMessageBox.information(self, "Select presets", "Tick at least two presets in the Compare column.")
            return
        baseline = selected[0]
        similarities = []
        aggregate: dict[str, list[float]] = {}
        for candidate in selected[1:]:
            similarity, scores = descriptor_similarity(baseline.descriptor, candidate.descriptor)
            similarities.append(similarity)
            for key, value in scores.items():
                aggregate.setdefault(key, []).append(value)
        overall = sum(similarities) / len(similarities)
        self.comparison_summary.setText(f"{baseline.name} compared with {', '.join(item.name for item in selected[1:])}: {overall:.1%} average similarity")
        self.breakdown.setRowCount(len(aggregate))
        for row, (key, values) in enumerate(aggregate.items()):
            self.breakdown.setItem(row, 0, QTableWidgetItem(key.replace("_", " ").title()))
            self.breakdown.setItem(row, 1, QTableWidgetItem(f"{sum(values) / len(values):.1%}"))
        self.store.add_history([item.name for item in selected], overall)
        self.refresh()

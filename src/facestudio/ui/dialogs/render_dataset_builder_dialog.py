from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QImageReader
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from facestudio.match_engine_research.geometry_dataset import HeadGeometryRecord
from facestudio.match_engine_research.one_click_face_builder import LANDMARK_ORDER, PhotoAnalysis
from facestudio.match_engine_research.render_dataset_builder import RenderCandidate, RenderDatasetBuilder
from facestudio.ui.widgets.landmark_editor import LandmarkEditor


class RenderDatasetBuilderDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("FM26 Calibrated Render Dataset Builder")
        self.resize(1280, 780)
        self.service = RenderDatasetBuilder()
        self.candidates: tuple[RenderCandidate, ...] = ()
        self.records: dict[str, HeadGeometryRecord] = {}
        self.current: RenderCandidate | None = None
        self.analysis: PhotoAnalysis | None = None
        self._syncing = False

        root = QVBoxLayout(self)
        intro = QLabel(
            "Choose a folder of standardised front-facing FM head renders named with numeric player IDs. "
            "Review each render by dragging its landmarks, accept it into the dataset, then export one calibrated geometry JSON file."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        actions = QHBoxLayout()
        choose = QPushButton("Choose calibrated render folder")
        choose.clicked.connect(self.choose_folder)
        self.folder_status = QLabel("No render folder selected")
        self.folder_status.setWordWrap(True)
        actions.addWidget(choose)
        actions.addWidget(self.folder_status, 1)
        root.addLayout(actions)

        body = QHBoxLayout()
        self.render_list = QListWidget()
        self.render_list.currentRowChanged.connect(self.load_row)
        body.addWidget(self.render_list, 1)

        centre = QVBoxLayout()
        self.canvas = LandmarkEditor()
        self.canvas.landmark_moved.connect(self.move_landmark)
        self.canvas.landmark_selected.connect(self.select_landmark)
        centre.addWidget(self.canvas, 1)
        choose_row = QHBoxLayout()
        self.landmark_name = QComboBox()
        self.landmark_name.addItems(LANDMARK_ORDER)
        self.landmark_name.currentTextChanged.connect(self.select_from_list)
        self.confidence = QSpinBox()
        self.confidence.setRange(50, 100)
        self.confidence.setValue(90)
        choose_row.addWidget(QLabel("Selected landmark"))
        choose_row.addWidget(self.landmark_name, 1)
        choose_row.addWidget(QLabel("Record confidence"))
        choose_row.addWidget(self.confidence)
        centre.addLayout(choose_row)
        self.current_status = QLabel("Select a render to begin")
        self.current_status.setWordWrap(True)
        centre.addWidget(self.current_status)
        body.addLayout(centre, 3)

        side = QVBoxLayout()
        self.measurements = QTextEdit()
        self.measurements.setReadOnly(True)
        self.measurements.setPlaceholderText("Measurements appear after loading a render")
        side.addWidget(self.measurements, 1)
        accept = QPushButton("Accept corrected render into dataset")
        accept.clicked.connect(self.accept_record)
        side.addWidget(accept)
        self.progress = QLabel("Accepted records: 0")
        side.addWidget(self.progress)
        export = QPushButton("Export calibrated geometry dataset")
        export.clicked.connect(self.export_dataset)
        side.addWidget(export)
        body.addLayout(side, 1)
        root.addLayout(body, 1)

        warning = QLabel(
            "Use only standardised front renders or independently decoded mesh evidence. Do not point this tool at FM UV texture PNGs."
        )
        warning.setWordWrap(True)
        warning.setStyleSheet("font-weight: 600;")
        root.addWidget(warning)

    def choose_folder(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Choose standardised FM head render folder")
        if not selected:
            return
        try:
            self.candidates = self.service.scan(Path(selected))
        except ValueError as exc:
            QMessageBox.critical(self, "Render folder rejected", str(exc))
            return
        self.records.clear()
        self.render_list.clear()
        for candidate in self.candidates:
            self.render_list.addItem(f"{candidate.player_id}  ·  pending")
        self.folder_status.setText(f"Loaded {len(self.candidates)} numeric-ID front renders from {selected}")
        self.progress.setText("Accepted records: 0")
        if self.candidates:
            self.render_list.setCurrentRow(0)

    def load_row(self, row: int) -> None:
        if row < 0 or row >= len(self.candidates):
            return
        self.current = self.candidates[row]
        try:
            self.analysis = self.service.analyse(self.current)
        except ValueError as exc:
            QMessageBox.critical(self, "Render error", str(exc))
            self.analysis = None
            return
        reader = QImageReader(self.current.front_render)
        reader.setAutoTransform(True)
        image = reader.read()
        self.canvas.set_content(image, self.analysis.landmarks)
        self.canvas.select_landmark(self.landmark_name.currentText())
        self.refresh_measurements()
        state = "already accepted" if self.current.player_id in self.records else "needs landmark review"
        self.current_status.setText(f"Player ID {self.current.player_id} · {state}. Drag at least one point before accepting.")

    def move_landmark(self, name: str, x: float, y: float) -> None:
        if self.analysis is None:
            return
        self.analysis = self.service.move_landmark(self.analysis, name, x, y)
        if self.current is not None:
            reader = QImageReader(self.current.front_render)
            reader.setAutoTransform(True)
            self.canvas.set_content(reader.read(), self.analysis.landmarks)
            self.canvas.select_landmark(name)
        self.select_landmark(name)
        self.refresh_measurements()

    def select_landmark(self, name: str) -> None:
        if self.landmark_name.currentText() != name:
            self._syncing = True
            self.landmark_name.setCurrentText(name)
            self._syncing = False

    def select_from_list(self, name: str) -> None:
        if not self._syncing:
            self.canvas.select_landmark(name)

    def refresh_measurements(self) -> None:
        if self.analysis is None:
            return
        values = self.analysis.measurements
        self.measurements.setPlainText(
            "Normalised calibrated-render measurements\n\n"
            f"Face width: {values.face_width:.3f}\n"
            f"Face height: {values.face_height:.3f}\n"
            f"Eye spacing: {values.eye_spacing:.3f}\n"
            f"Nose length: {values.nose_length:.3f}\n"
            f"Mouth width: {values.mouth_width:.3f}\n"
            f"Jaw width: {values.jaw_width:.3f}\n"
            f"Chin length: {values.chin_length:.3f}\n"
            f"Symmetry: {values.symmetry:.3f}"
        )

    def accept_record(self) -> None:
        if self.current is None or self.analysis is None:
            QMessageBox.warning(self, "Render required", "Select and review a front render first.")
            return
        try:
            record = self.service.make_record(self.current, self.analysis, self.confidence.value() / 100.0)
        except ValueError as exc:
            QMessageBox.warning(self, "Correction required", str(exc))
            return
        self.records[record.player_id] = record
        row = self.render_list.currentRow()
        self.render_list.item(row).setText(f"{record.player_id}  ·  accepted {record.confidence:.2f}")
        self.progress.setText(f"Accepted records: {len(self.records)} of {len(self.candidates)}")
        if row + 1 < len(self.candidates):
            self.render_list.setCurrentRow(row + 1)

    def export_dataset(self) -> None:
        if not self.records:
            QMessageBox.warning(self, "No records", "Accept at least one corrected render first.")
            return
        selected, _ = QFileDialog.getSaveFileName(
            self, "Export calibrated FM26 geometry dataset", "facestudio-fm-head-geometry.json", "JSON files (*.json)"
        )
        if not selected:
            return
        ordered = tuple(self.records[key] for key in sorted(self.records, key=int))
        try:
            destination = self.service.save(ordered, Path(selected))
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Export failed", str(exc))
            return
        QMessageBox.information(self, "Dataset exported", f"Saved {len(ordered)} calibrated records to:\n{destination}")

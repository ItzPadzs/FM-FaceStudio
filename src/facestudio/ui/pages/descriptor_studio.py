from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from facestudio.matching.engine import FaceMatcher
from facestudio.matching.models import FaceDescriptor, MatchCandidate
from facestudio.matching.presets import DescriptorPresetStore
from facestudio.projects.model import FaceStudioProject
from facestudio.ui.widgets.radar_chart import RadarChart


class DescriptorSlider(QWidget):
    value_changed = Signal(float)

    def __init__(
        self,
        minimum: float,
        maximum: float,
        step: float,
    ) -> None:
        super().__init__()
        self.minimum = minimum
        self.maximum = maximum
        self.step = step

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(
            0,
            round((maximum - minimum) / step),
        )
        self.value_label = QLabel("0.000")
        self.value_label.setMinimumWidth(58)

        self.slider.valueChanged.connect(self._emit_value)
        layout.addWidget(self.slider, 1)
        layout.addWidget(self.value_label)

    def _emit_value(self, raw: int) -> None:
        value = self.minimum + raw * self.step
        self.value_label.setText(f"{value:.3f}")
        self.value_changed.emit(value)

    def set_value(self, value: float) -> None:
        clamped = max(self.minimum, min(self.maximum, value))
        raw = round((clamped - self.minimum) / self.step)
        self.slider.blockSignals(True)
        self.slider.setValue(raw)
        self.slider.blockSignals(False)
        self.value_label.setText(f"{clamped:.3f}")

    def value(self) -> float:
        return self.minimum + self.slider.value() * self.step


class DescriptorStudioPage(QWidget):
    descriptor_saved = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.project: FaceStudioProject | None = None
        self.directory: Path | None = None
        self.original: FaceDescriptor | None = None
        self.comparison: FaceDescriptor | None = None
        self.preset_store = DescriptorPresetStore()
        self.matcher = FaceMatcher()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("Descriptor Studio")
        title.setObjectName("PageTitle")
        header.addWidget(title)
        header.addStretch()

        self.reset_button = QPushButton("Reset to analysis")
        self.reset_button.clicked.connect(self.reset_to_analysis)
        save_button = QPushButton("Save preset…")
        save_button.clicked.connect(self.save_preset)
        load_button = QPushButton("Load comparison…")
        load_button.clicked.connect(self.load_comparison)
        header.addWidget(self.reset_button)
        header.addWidget(save_button)
        header.addWidget(load_button)
        layout.addLayout(header)

        notice = QLabel(
            "Edit descriptor measurements, compare a second preset and inspect "
            "the live similarity breakdown. Changes here do not overwrite the "
            "original analysis unless saved as a separate preset."
        )
        notice.setObjectName("Muted")
        notice.setWordWrap(True)
        layout.addWidget(notice)

        body = QHBoxLayout()

        controls = QGroupBox("Editable descriptor")
        controls_layout = QFormLayout(controls)

        self.face_ratio = DescriptorSlider(0.80, 1.70, 0.005)
        self.eye_spacing = DescriptorSlider(0.20, 0.50, 0.002)
        self.eye_line = DescriptorSlider(0.20, 0.60, 0.002)
        self.mouth_line = DescriptorSlider(0.55, 0.90, 0.002)

        for widget in (
            self.face_ratio,
            self.eye_spacing,
            self.eye_line,
            self.mouth_line,
        ):
            widget.value_changed.connect(self.refresh_live_view)

        self.shape = QComboBox()
        self.shape.addItems(
            ["round", "square / round", "oval", "oblong", "undetermined"]
        )
        self.shape.currentTextChanged.connect(self.refresh_live_view)

        controls_layout.addRow("Face height / width", self.face_ratio)
        controls_layout.addRow("Eye spacing / width", self.eye_spacing)
        controls_layout.addRow("Eye line / height", self.eye_line)
        controls_layout.addRow("Mouth line / height", self.mouth_line)
        controls_layout.addRow("Face shape", self.shape)

        self.similarity_label = QLabel("No comparison preset loaded.")
        self.similarity_label.setWordWrap(True)
        controls_layout.addRow("Comparison", self.similarity_label)
        body.addWidget(controls, 1)

        visual_group = QGroupBox("Descriptor profile")
        visual_layout = QVBoxLayout(visual_group)
        self.radar = RadarChart()
        visual_layout.addWidget(self.radar)
        body.addWidget(visual_group, 1)

        layout.addLayout(body)

        breakdown = QGroupBox("Live similarity breakdown")
        breakdown_layout = QVBoxLayout(breakdown)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(
            ["Component", "Similarity", "Explanation"]
        )
        self.table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        breakdown_layout.addWidget(self.table)
        layout.addWidget(breakdown, 1)

        self.set_enabled(False)

    def set_enabled(self, enabled: bool) -> None:
        self.reset_button.setEnabled(enabled)
        for widget in (
            self.face_ratio,
            self.eye_spacing,
            self.eye_line,
            self.mouth_line,
            self.shape,
        ):
            widget.setEnabled(enabled)

    def set_project(
        self,
        project: FaceStudioProject | None,
        directory: Path | None,
    ) -> None:
        self.project = project
        self.directory = directory
        self.original = None
        self.comparison = None

        if not project or not directory or not project.analysis_file:
            self.set_enabled(False)
            self.similarity_label.setText(
                "Run Face Analysis for the current project first."
            )
            self.radar.set_descriptors(None, None)
            self.table.setRowCount(0)
            return

        analysis_path = directory / project.analysis_file
        if not analysis_path.exists():
            self.set_enabled(False)
            return

        payload = json.loads(analysis_path.read_text(encoding="utf-8"))
        self.original = FaceDescriptor.from_analysis_payload(payload)
        self.set_enabled(True)
        self.reset_to_analysis()

    def current_descriptor(self) -> FaceDescriptor:
        return FaceDescriptor(
            face_height_width_ratio=self.face_ratio.value(),
            inter_eye_face_width_ratio=self.eye_spacing.value(),
            eye_line_face_height_ratio=self.eye_line.value(),
            mouth_line_face_height_ratio=self.mouth_line.value(),
            face_shape=self.shape.currentText(),
        )

    def reset_to_analysis(self) -> None:
        if self.original is None:
            return
        self.face_ratio.set_value(
            self.original.face_height_width_ratio
        )
        self.eye_spacing.set_value(
            self.original.inter_eye_face_width_ratio
        )
        self.eye_line.set_value(
            self.original.eye_line_face_height_ratio
        )
        self.mouth_line.set_value(
            self.original.mouth_line_face_height_ratio
        )
        self.shape.setCurrentText(self.original.face_shape)
        self.refresh_live_view()

    def save_preset(self) -> None:
        if self.directory is None:
            return
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save descriptor preset",
            str(self.directory / "descriptor-preset.json"),
            "FaceStudio descriptor (*.json)",
        )
        if filename:
            self.preset_store.save(
                self.current_descriptor(),
                Path(filename),
            )
            self.descriptor_saved.emit()

    def load_comparison(self) -> None:
        start = str(self.directory or Path.home())
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Load comparison descriptor",
            start,
            "FaceStudio descriptor (*.json)",
        )
        if filename:
            self.comparison = self.preset_store.load(Path(filename))
            self.refresh_live_view()

    def refresh_live_view(self, *args) -> None:
        if self.original is None:
            return
        current = self.current_descriptor()
        self.radar.set_descriptors(current, self.comparison)

        reference = self.comparison or self.original
        candidate = MatchCandidate(
            candidate_id="comparison",
            display_name="Comparison",
            descriptor=reference,
        )
        result = self.matcher.compare(current, candidate)

        label = (
            "Compared with loaded preset"
            if self.comparison is not None
            else "Compared with original analysis"
        )
        self.similarity_label.setText(
            f"{label}: {result.similarity:.1%}"
        )

        explanations = {
            "face_height_width_ratio": "Overall facial length compared with width.",
            "inter_eye_face_width_ratio": "Spacing between eyes compared with face width.",
            "eye_line_face_height_ratio": "Vertical eye position within the face.",
            "mouth_line_face_height_ratio": "Vertical mouth position within the face.",
            "face_shape": "Compatibility of the broad geometric face-shape label.",
        }

        self.table.setRowCount(len(result.component_scores))
        for row, (name, score) in enumerate(result.component_scores.items()):
            display_name = name.replace("_", " ").title()
            self.table.setItem(row, 0, QTableWidgetItem(display_name))
            self.table.setItem(row, 1, QTableWidgetItem(f"{score:.1%}"))
            self.table.setItem(
                row,
                2,
                QTableWidgetItem(explanations.get(name, "")),
            )

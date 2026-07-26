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
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from facestudio.matching.engine import FaceMatcher
from facestudio.matching.models import FaceDescriptor, MatchCandidate
from facestudio.matching.presets import DescriptorPresetStore
from facestudio.projects.model import FaceStudioProject
from facestudio.ui.widgets.activity_banner import ActivityBanner
from facestudio.ui.widgets.page_header import PageHeader
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
        layout.setSpacing(10)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, round((maximum - minimum) / step))
        self.value_label = QLabel("0.000")
        self.value_label.setObjectName("MetricValue")
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
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(18)

        self.reset_button = QPushButton("Reset to analysis")
        self.reset_button.setObjectName("Secondary")
        self.reset_button.clicked.connect(self.reset_to_analysis)
        self.save_button = QPushButton("Save preset…")
        self.save_button.setObjectName("Primary")
        self.save_button.clicked.connect(self.save_preset)
        self.load_button = QPushButton("Load comparison…")
        self.load_button.setObjectName("Secondary")
        self.load_button.clicked.connect(self.load_comparison)

        layout.addWidget(
            PageHeader(
                "Descriptor refinement",
                "Descriptor Studio",
                "Adjust transparent face measurements, compare a second preset "
                "and inspect live descriptor similarity. The original analysis "
                "is preserved unless a separate preset is explicitly saved.",
                [self.reset_button, self.load_button, self.save_button],
            )
        )

        self.activity = ActivityBanner(
            "Run Face Analysis for the current project to unlock the studio."
        )
        layout.addWidget(self.activity)

        body = QHBoxLayout()
        body.setSpacing(16)

        controls = QGroupBox("Editable descriptor")
        controls.setObjectName("WorkspaceCard")
        controls_layout = QFormLayout(controls)
        controls_layout.setContentsMargins(16, 20, 16, 16)
        controls_layout.setHorizontalSpacing(18)
        controls_layout.setVerticalSpacing(14)

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
        self.similarity_label.setObjectName("MetricValue")
        self.similarity_label.setWordWrap(True)
        controls_layout.addRow("Comparison", self.similarity_label)
        body.addWidget(controls, 1)

        visual_group = QGroupBox("Descriptor profile")
        visual_group.setObjectName("WorkspaceCard")
        visual_layout = QVBoxLayout(visual_group)
        visual_layout.setContentsMargins(16, 20, 16, 16)
        self.radar = RadarChart()
        visual_layout.addWidget(self.radar)
        body.addWidget(visual_group, 1)

        layout.addLayout(body)

        breakdown = QGroupBox("Live similarity breakdown")
        breakdown.setObjectName("WorkspaceCard")
        breakdown_layout = QVBoxLayout(breakdown)
        breakdown_layout.setContentsMargins(12, 18, 12, 12)
        self.table = QTableWidget(0, 3)
        self.table.setObjectName("ResultsTable")
        self.table.setHorizontalHeaderLabels(
            ["Component", "Similarity", "Explanation"]
        )
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        breakdown_layout.addWidget(self.table)
        layout.addWidget(breakdown, 1)

        self.set_enabled(False)

    def set_enabled(self, enabled: bool) -> None:
        for widget in (
            self.reset_button,
            self.save_button,
            self.load_button,
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
            self.activity.set_state(
                "Run Face Analysis for the current project to unlock the studio."
            )
            self.radar.set_descriptors(None, None)
            self.table.setRowCount(0)
            return

        analysis_path = directory / project.analysis_file
        if not analysis_path.exists():
            self.set_enabled(False)
            self.activity.set_state("The saved analysis file could not be found.")
            return

        try:
            payload = json.loads(analysis_path.read_text(encoding="utf-8"))
            self.original = FaceDescriptor.from_analysis_payload(payload)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            self.set_enabled(False)
            self.activity.set_state(f"Unable to load the saved analysis: {exc}")
            return

        self.set_enabled(True)
        self.reset_to_analysis()
        self.activity.set_state(
            "Analysis loaded. Adjust measurements or load a comparison preset."
        )

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
        self.face_ratio.set_value(self.original.face_height_width_ratio)
        self.eye_spacing.set_value(self.original.inter_eye_face_width_ratio)
        self.eye_line.set_value(self.original.eye_line_face_height_ratio)
        self.mouth_line.set_value(self.original.mouth_line_face_height_ratio)
        self.shape.setCurrentText(self.original.face_shape)
        self.refresh_live_view()
        self.activity.set_state("Descriptor reset to the original analysis values.")

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
            self.preset_store.save(self.current_descriptor(), Path(filename))
            self.activity.set_state(f"Descriptor preset saved to {filename}.")
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
            self.activity.set_state(f"Comparison preset loaded: {filename}")

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
        self.similarity_label.setText(f"{label}: {result.similarity:.1%}")

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

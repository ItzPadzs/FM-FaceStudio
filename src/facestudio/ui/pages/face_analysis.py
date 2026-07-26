from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from facestudio.ai.models import FaceAnalysis
from facestudio.projects.model import FaceStudioProject
from facestudio.ui.widgets.activity_banner import ActivityBanner
from facestudio.ui.widgets.page_header import PageHeader


class FaceAnalysisPage(QWidget):
    analyze_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.project: FaceStudioProject | None = None
        self.directory: Path | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(18)

        self.analyze_button = QPushButton("Analyse photograph")
        self.analyze_button.setObjectName("Primary")
        self.analyze_button.clicked.connect(self.analyze_requested.emit)

        layout.addWidget(
            PageHeader(
                "Source-photo workflow",
                "Face Analysis",
                "Detect one clear frontal face, estimate reusable feature anchors "
                "and save transparent measurements inside the current project. "
                "Detected anchors and proportional estimates remain clearly labelled.",
                [self.analyze_button],
            )
        )

        self.activity = ActivityBanner(
            "Open a project and import a source photograph to begin."
        )
        layout.addWidget(self.activity)

        splitter = QSplitter()
        splitter.setChildrenCollapsible(False)

        preview_group = QGroupBox("Analysis preview")
        preview_group.setObjectName("WorkspaceCard")
        preview_layout = QVBoxLayout(preview_group)
        preview_layout.setContentsMargins(14, 20, 14, 14)
        self.preview = QLabel("No analysis preview")
        self.preview.setObjectName("PreviewSurface")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumSize(520, 480)
        preview_layout.addWidget(self.preview)
        splitter.addWidget(preview_group)

        result_group = QGroupBox("Face descriptor")
        result_group.setObjectName("WorkspaceCard")
        result_layout = QVBoxLayout(result_group)
        result_layout.setContentsMargins(16, 20, 16, 16)
        form = QFormLayout()
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(10)
        self.shape = QLabel("—")
        self.confidence = QLabel("—")
        self.face_ratio = QLabel("—")
        self.eye_ratio = QLabel("—")
        self.mouth_ratio = QLabel("—")
        self.detected_count = QLabel("—")
        for label in (
            self.shape,
            self.confidence,
            self.face_ratio,
            self.eye_ratio,
            self.mouth_ratio,
            self.detected_count,
        ):
            label.setObjectName("MetricValue")
        form.addRow("Broad face shape", self.shape)
        form.addRow("Overall confidence", self.confidence)
        form.addRow("Height / width", self.face_ratio)
        form.addRow("Eye spacing / width", self.eye_ratio)
        form.addRow("Mouth line / height", self.mouth_ratio)
        form.addRow("Detected anchors", self.detected_count)
        result_layout.addLayout(form)

        self.details = QPlainTextEdit()
        self.details.setObjectName("AnalysisDetails")
        self.details.setReadOnly(True)
        self.details.setPlaceholderText(
            "Landmark details and analysis notes will appear here."
        )
        result_layout.addWidget(self.details, 1)
        splitter.addWidget(result_group)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter, 1)
        self.analyze_button.setEnabled(False)

    def set_project(
        self,
        project: FaceStudioProject | None,
        directory: Path | None,
    ) -> None:
        self.project = project
        self.directory = directory
        has_photo = bool(project and directory and project.source_photo)
        self.analyze_button.setEnabled(has_photo)

        if not project or not directory:
            self.activity.set_state(
                "Open a project and import a source photograph to begin."
            )
            self.clear_results()
            return

        if not project.source_photo:
            self.activity.set_state(
                "Import a source photograph from the Project page first."
            )
            self.clear_results()
            return

        self.activity.set_state(
            f"Ready to analyse: {directory / project.source_photo}"
        )
        if project.analysis_file and (directory / project.analysis_file).exists():
            self.load_saved_analysis(directory / project.analysis_file)
            self.activity.set_state("Saved analysis loaded for the current project.")
        if project.preview_file and (directory / project.preview_file).exists():
            self.set_preview(directory / project.preview_file)

    def set_busy(self, busy: bool, message: str = "") -> None:
        self.analyze_button.setEnabled(
            not busy and bool(self.project and self.project.source_photo)
        )
        self.activity.set_state(message or "Analysing source photograph…", busy)

    def show_analysis(
        self,
        analysis: FaceAnalysis,
        preview_path: Path,
    ) -> None:
        self.shape.setText(analysis.face_shape)
        self.confidence.setText(f"{analysis.confidence:.0%}")
        self.face_ratio.setText(
            f"{analysis.measurements['face_height_width_ratio']:.3f}"
        )
        self.eye_ratio.setText(
            f"{analysis.measurements['inter_eye_face_width_ratio']:.3f}"
        )
        self.mouth_ratio.setText(
            f"{analysis.measurements['mouth_line_face_height_ratio']:.3f}"
        )
        detected = sum(
            point.source == "detected" for point in analysis.landmarks.values()
        )
        self.detected_count.setText(f"{detected} of {len(analysis.landmarks)}")
        lines = []
        for name, point in analysis.landmarks.items():
            lines.append(
                f"{name}: ({point.x:.4f}, {point.y:.4f}) — "
                f"{point.source}, confidence {point.confidence:.0%}"
            )
        if analysis.notes:
            lines.extend(["", "Notes:", *analysis.notes])
        self.details.setPlainText("\n".join(lines))
        self.set_preview(preview_path)
        self.activity.set_state(
            "Analysis complete. Results were saved inside the project."
        )

    def load_saved_analysis(self, path: Path) -> None:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        self.shape.setText(str(payload.get("face_shape", "—")))
        confidence = float(payload.get("confidence", 0.0))
        self.confidence.setText(f"{confidence:.0%}")
        measurements = payload.get("measurements", {})
        self.face_ratio.setText(
            str(measurements.get("face_height_width_ratio", "—"))
        )
        self.eye_ratio.setText(
            str(measurements.get("inter_eye_face_width_ratio", "—"))
        )
        self.mouth_ratio.setText(
            str(measurements.get("mouth_line_face_height_ratio", "—"))
        )
        landmarks = payload.get("landmarks", {})
        detected = sum(
            item.get("source") == "detected"
            for item in landmarks.values()
            if isinstance(item, dict)
        )
        self.detected_count.setText(f"{detected} of {len(landmarks)}")
        self.details.setPlainText(json.dumps(payload, indent=2))

    def set_preview(self, path: Path) -> None:
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            self.preview.setText("Unable to load preview")
            return
        self.preview.setPixmap(
            pixmap.scaled(
                760,
                620,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        self.preview.setText("")

    def clear_results(self) -> None:
        self.preview.setPixmap(QPixmap())
        self.preview.setText("No analysis preview")
        for label in (
            self.shape,
            self.confidence,
            self.face_ratio,
            self.eye_ratio,
            self.mouth_ratio,
            self.detected_count,
        ):
            label.setText("—")
        self.details.clear()

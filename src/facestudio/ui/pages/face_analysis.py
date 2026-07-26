from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from facestudio.ai.models import FaceAnalysis
from facestudio.projects.model import FaceStudioProject


class FaceAnalysisPage(QWidget):
    analyze_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.project: FaceStudioProject | None = None
        self.directory: Path | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("Face Analysis")
        title.setObjectName("PageTitle")
        header.addWidget(title)
        header.addStretch()
        self.analyze_button = QPushButton("Analyse photograph")
        self.analyze_button.setObjectName("Primary")
        self.analyze_button.clicked.connect(self.analyze_requested.emit)
        header.addWidget(self.analyze_button)
        layout.addLayout(header)

        explanation = QLabel(
            "Detects one clear frontal face, estimates key feature anchors and "
            "stores reusable measurements in the current project. Green markers "
            "are detected; amber markers are proportional estimates."
        )
        explanation.setObjectName("Muted")
        explanation.setWordWrap(True)
        layout.addWidget(explanation)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        self.status_label = QLabel("Open a project and import a source photograph.")
        self.status_label.setObjectName("Muted")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        splitter = QSplitter()

        preview_group = QGroupBox("Analysis preview")
        preview_layout = QVBoxLayout(preview_group)
        self.preview = QLabel("No analysis preview")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumSize(520, 480)
        self.preview.setStyleSheet(
            "border: 1px dashed #4a505b; border-radius: 8px;"
        )
        preview_layout.addWidget(self.preview)
        splitter.addWidget(preview_group)

        result_group = QGroupBox("Face descriptor")
        result_layout = QVBoxLayout(result_group)
        form = QFormLayout()
        self.shape = QLabel("—")
        self.confidence = QLabel("—")
        self.face_ratio = QLabel("—")
        self.eye_ratio = QLabel("—")
        self.mouth_ratio = QLabel("—")
        self.detected_count = QLabel("—")
        form.addRow("Broad face shape", self.shape)
        form.addRow("Overall confidence", self.confidence)
        form.addRow("Height / width", self.face_ratio)
        form.addRow("Eye spacing / width", self.eye_ratio)
        form.addRow("Mouth line / height", self.mouth_ratio)
        form.addRow("Detected anchors", self.detected_count)
        result_layout.addLayout(form)

        self.details = QPlainTextEdit()
        self.details.setReadOnly(True)
        self.details.setPlaceholderText(
            "Landmark details and analysis notes will appear here."
        )
        result_layout.addWidget(self.details, 1)
        splitter.addWidget(result_group)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter, 1)

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
            self.status_label.setText(
                "Open a project and import a source photograph."
            )
            self.clear_results()
            return

        if not project.source_photo:
            self.status_label.setText(
                "Import a source photograph from the Project page first."
            )
            self.clear_results()
            return

        self.status_label.setText(
            f"Ready to analyse: {directory / project.source_photo}"
        )
        if project.analysis_file and (directory / project.analysis_file).exists():
            self.load_saved_analysis(directory / project.analysis_file)
        if project.preview_file and (directory / project.preview_file).exists():
            self.set_preview(directory / project.preview_file)

    def set_busy(self, busy: bool, message: str = "") -> None:
        self.progress.setVisible(busy)
        self.analyze_button.setEnabled(not busy and bool(
            self.project and self.project.source_photo
        ))
        if message:
            self.status_label.setText(message)

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
            point.source == "detected"
            for point in analysis.landmarks.values()
        )
        self.detected_count.setText(
            f"{detected} of {len(analysis.landmarks)}"
        )
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
        self.status_label.setText(
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

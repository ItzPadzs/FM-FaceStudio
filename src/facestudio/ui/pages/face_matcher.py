from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from facestudio.matching.models import MatchResult
from facestudio.projects.model import FaceStudioProject


class FaceMatcherPage(QWidget):
    match_requested = Signal(str)

    def __init__(self, default_catalogue_path: Path) -> None:
        super().__init__()
        self.project: FaceStudioProject | None = None
        self.directory: Path | None = None
        self.catalogue_path = default_catalogue_path

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("Face Matcher")
        title.setObjectName("PageTitle")
        header.addWidget(title)
        header.addStretch()

        self.choose_catalogue = QPushButton("Choose catalogue…")
        self.choose_catalogue.clicked.connect(self._choose_catalogue)
        self.match_button = QPushButton("Find closest matches")
        self.match_button.setObjectName("Primary")
        self.match_button.clicked.connect(
            lambda: self.match_requested.emit(str(self.catalogue_path))
        )
        header.addWidget(self.choose_catalogue)
        header.addWidget(self.match_button)
        layout.addLayout(header)

        explanation = QLabel(
            "Compares the current project descriptor against a catalogue of "
            "FaceStudio descriptors. This sprint uses a transparent sample "
            "catalogue and does not claim to match proprietary FM head meshes."
        )
        explanation.setObjectName("Muted")
        explanation.setWordWrap(True)
        layout.addWidget(explanation)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        details = QGroupBox("Matching source")
        form = QFormLayout(details)
        self.analysis_label = QLabel("No project analysis available")
        self.analysis_label.setWordWrap(True)
        self.catalogue_label = QLabel(str(self.catalogue_path))
        self.catalogue_label.setWordWrap(True)
        self.result_label = QLabel("No matches calculated")
        self.result_label.setWordWrap(True)
        form.addRow("Analysis", self.analysis_label)
        form.addRow("Catalogue", self.catalogue_label)
        form.addRow("Status", self.result_label)
        layout.addWidget(details)

        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(
            [
                "Rank",
                "Candidate",
                "Similarity",
                "Shape",
                "Face ratio",
                "Eye spacing",
                "Mouth line",
                "Source",
            ]
        )
        self.table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self.table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 1)

    def _choose_catalogue(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Choose FaceStudio candidate catalogue",
            str(self.catalogue_path.parent),
            "JSON catalogues (*.json)",
        )
        if filename:
            self.catalogue_path = Path(filename)
            self.catalogue_label.setText(filename)

    def set_project(
        self,
        project: FaceStudioProject | None,
        directory: Path | None,
    ) -> None:
        self.project = project
        self.directory = directory
        ready = bool(
            project
            and directory
            and project.analysis_file
            and (directory / project.analysis_file).exists()
        )
        self.match_button.setEnabled(ready)
        if ready:
            self.analysis_label.setText(
                str(directory / project.analysis_file)
            )
            self.result_label.setText("Ready to compare descriptors.")
        else:
            self.analysis_label.setText(
                "Run Face Analysis for the current project first."
            )
            self.result_label.setText("No matches calculated.")
            self.table.setRowCount(0)

    def set_busy(self, busy: bool, message: str = "") -> None:
        self.progress.setVisible(busy)
        self.match_button.setEnabled(
            not busy
            and bool(
                self.project
                and self.directory
                and self.project.analysis_file
            )
        )
        if message:
            self.result_label.setText(message)

    def show_results(
        self,
        results: list[MatchResult],
        output_path: Path,
    ) -> None:
        self.table.setRowCount(len(results))
        for row, result in enumerate(results):
            descriptor = result.candidate.descriptor
            values = [
                str(row + 1),
                result.candidate.display_name,
                f"{result.similarity:.1%}",
                descriptor.face_shape,
                f"{descriptor.face_height_width_ratio:.3f}",
                f"{descriptor.inter_eye_face_width_ratio:.3f}",
                f"{descriptor.mouth_line_face_height_ratio:.3f}",
                result.candidate.source,
            ]
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(value))

        self.result_label.setText(
            f"Calculated {len(results)} matches. Saved to {output_path}."
        )

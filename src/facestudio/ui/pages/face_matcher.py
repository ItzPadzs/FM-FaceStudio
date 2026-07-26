from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from facestudio.matching.models import MatchResult
from facestudio.projects.model import FaceStudioProject
from facestudio.ui.widgets.activity_banner import ActivityBanner
from facestudio.ui.widgets.page_header import PageHeader


class FaceMatcherPage(QWidget):
    match_requested = Signal(str)

    def __init__(self, default_catalogue_path: Path) -> None:
        super().__init__()
        self.project: FaceStudioProject | None = None
        self.directory: Path | None = None
        self.catalogue_path = default_catalogue_path

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(18)

        self.choose_catalogue = QPushButton("Choose catalogue…")
        self.choose_catalogue.setObjectName("Secondary")
        self.choose_catalogue.clicked.connect(self._choose_catalogue)

        self.match_button = QPushButton("Find closest matches")
        self.match_button.setObjectName("Primary")
        self.match_button.clicked.connect(
            lambda: self.match_requested.emit(str(self.catalogue_path))
        )

        layout.addWidget(
            PageHeader(
                "Descriptor matching",
                "Face Matcher",
                "Compare the current analysed descriptor against a transparent "
                "FaceStudio catalogue. Results describe descriptor similarity and "
                "do not claim proprietary Football Manager head-mesh matching.",
                [self.choose_catalogue, self.match_button],
            )
        )

        self.activity = ActivityBanner(
            "Run Face Analysis for the current project before matching."
        )
        layout.addWidget(self.activity)

        details = QGroupBox("Matching source")
        details.setObjectName("WorkspaceCard")
        form = QFormLayout(details)
        form.setContentsMargins(16, 20, 16, 16)
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(12)

        self.analysis_label = QLabel("No project analysis available")
        self.analysis_label.setWordWrap(True)
        self.catalogue_label = QLabel(str(self.catalogue_path))
        self.catalogue_label.setWordWrap(True)
        self.result_label = QLabel("No matches calculated")
        self.result_label.setWordWrap(True)
        form.addRow("Analysis", self.analysis_label)
        form.addRow("Catalogue", self.catalogue_label)
        form.addRow("Results", self.result_label)
        layout.addWidget(details)

        results_box = QGroupBox("Ranked descriptor matches")
        results_box.setObjectName("WorkspaceCard")
        results_layout = QVBoxLayout(results_box)
        results_layout.setContentsMargins(12, 18, 12, 12)

        self.table = QTableWidget(0, 8)
        self.table.setObjectName("ResultsTable")
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
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        results_layout.addWidget(self.table)
        layout.addWidget(results_box, 1)

        self.match_button.setEnabled(False)

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
            self.activity.set_state("Catalogue selected. Ready to compare descriptors.")

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
            analysis_path = directory / project.analysis_file
            self.analysis_label.setText(str(analysis_path))
            self.result_label.setText("Ready to calculate ranked matches.")
            self.activity.set_state("Analysis loaded. Choose a catalogue or start matching.")
        else:
            self.analysis_label.setText(
                "Run Face Analysis for the current project first."
            )
            self.result_label.setText("No matches calculated.")
            self.activity.set_state(
                "Run Face Analysis for the current project before matching."
            )
            self.table.setRowCount(0)

    def set_busy(self, busy: bool, message: str = "") -> None:
        self.match_button.setEnabled(
            not busy
            and bool(
                self.project
                and self.directory
                and self.project.analysis_file
            )
        )
        self.choose_catalogue.setEnabled(not busy)
        self.activity.set_state(message or "Calculating descriptor matches…", busy)
        if message:
            self.result_label.setText(message)

    def show_results(
        self,
        results: list[MatchResult],
        output_path: Path,
    ) -> None:
        self.table.setSortingEnabled(False)
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
        self.table.setSortingEnabled(True)

        summary = f"Calculated {len(results)} matches. Saved to {output_path}."
        self.result_label.setText(summary)
        self.activity.set_state(summary)

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from facestudio.ui.widgets.activity_banner import ActivityBanner
from facestudio.ui.widgets.page_header import PageHeader


class BatchAnalysisPage(QWidget):
    start_requested = Signal(object, str)
    cancel_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.sources: list[Path] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(16)

        self.add_button = QPushButton("Add photographs…")
        self.add_button.setObjectName("Secondary")
        self.add_button.clicked.connect(self._choose_sources)
        self.start_button = QPushButton("Analyse batch")
        self.start_button.setObjectName("Primary")
        self.start_button.clicked.connect(self._start)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_requested.emit)
        clear_button = QPushButton("Clear queue")
        clear_button.clicked.connect(self.clear_queue)

        layout.addWidget(PageHeader(
            "Multi-image research",
            "Batch Analysis",
            "Analyse a queue of standard photographs sequentially, preserve an individual transparent analysis for each image and add successful results to the Face Library.",
            [clear_button, self.add_button, self.start_button, self.cancel_button],
        ))

        self.activity = ActivityBanner("Add photographs and choose an output folder to begin.")
        layout.addWidget(self.activity)

        output_box = QGroupBox("Batch output")
        output_box.setObjectName("WorkspaceCard")
        output_layout = QHBoxLayout(output_box)
        self.output_path = QLineEdit()
        self.output_path.setPlaceholderText("Choose a folder for batch analysis results")
        browse_output = QPushButton("Choose folder…")
        browse_output.clicked.connect(self._choose_output)
        output_layout.addWidget(self.output_path, 1)
        output_layout.addWidget(browse_output)
        layout.addWidget(output_box)

        queue_box = QGroupBox("Analysis queue")
        queue_box.setObjectName("WorkspaceCard")
        queue_layout = QVBoxLayout(queue_box)
        self.summary = QLabel("No photographs queued.")
        self.summary.setObjectName("Muted")
        queue_layout.addWidget(self.summary)
        self.table = QTableWidget(0, 4)
        self.table.setObjectName("ResultsTable")
        self.table.setHorizontalHeaderLabels(["Photograph", "Status", "Face shape", "Confidence"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        queue_layout.addWidget(self.table)
        layout.addWidget(queue_box, 1)

    def _choose_sources(self) -> None:
        filenames, _ = QFileDialog.getOpenFileNames(
            self,
            "Choose photographs for batch analysis",
            "",
            "Images (*.jpg *.jpeg *.png *.webp *.bmp)",
        )
        existing = {str(path.resolve()) for path in self.sources}
        for filename in filenames:
            path = Path(filename)
            if str(path.resolve()) not in existing:
                self.sources.append(path)
                existing.add(str(path.resolve()))
        self._rebuild_queue()

    def _choose_output(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Choose batch output folder")
        if directory:
            self.output_path.setText(directory)

    def _start(self) -> None:
        output = self.output_path.text().strip()
        if not self.sources:
            self.activity.set_state("Add at least one photograph before starting.")
            return
        if not output:
            self.activity.set_state("Choose an output folder before starting.")
            return
        self.start_requested.emit(list(self.sources), output)

    def _rebuild_queue(self) -> None:
        self.table.setRowCount(len(self.sources))
        for row, source in enumerate(self.sources):
            self.table.setItem(row, 0, QTableWidgetItem(source.name))
            self.table.setItem(row, 1, QTableWidgetItem("Queued"))
            self.table.setItem(row, 2, QTableWidgetItem("—"))
            self.table.setItem(row, 3, QTableWidgetItem("—"))
        self.summary.setText(f"{len(self.sources):,} photograph(s) queued." if self.sources else "No photographs queued.")

    def clear_queue(self) -> None:
        if self.cancel_button.isEnabled():
            return
        self.sources.clear()
        self._rebuild_queue()

    def set_running(self, running: bool) -> None:
        self.add_button.setEnabled(not running)
        self.start_button.setEnabled(not running)
        self.cancel_button.setEnabled(running)
        self.output_path.setEnabled(not running)
        if running:
            for row in range(self.table.rowCount()):
                self.table.item(row, 1).setText("Waiting")

    def update_progress(self, index: int, total: int, filename: str) -> None:
        row = index - 1
        if 0 <= row < self.table.rowCount():
            self.table.item(row, 1).setText("Analysing")
        self.activity.set_state(f"Analysing {index} of {total}: {filename}", busy=True)

    def mark_completed(self, result: dict) -> None:
        source_name = Path(str(result.get("source_path", ""))).name
        for row, source in enumerate(self.sources):
            if source.stem == str(result.get("name", "")) or source.name == source_name:
                self.table.item(row, 1).setText("Complete")
                self.table.item(row, 2).setText(str(result.get("face_shape", "undetermined")))
                self.table.item(row, 3).setText(f"{float(result.get('confidence', 0.0)):.0%}")
                break

    def mark_failed(self, filename: str, message: str) -> None:
        for row, source in enumerate(self.sources):
            if source.name == filename:
                self.table.item(row, 1).setText("Failed")
                self.table.item(row, 2).setText(message[:80])
                break

    def finish(self, succeeded: int, failed: int) -> None:
        self.set_running(False)
        self.activity.set_state(
            f"Batch complete: {succeeded} succeeded and {failed} failed. Successful analyses were added to the Face Library."
        )

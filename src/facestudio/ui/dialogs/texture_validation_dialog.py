from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from facestudio.match_engine_research.texture_validation import TextureValidationService, ValidationResult


class TextureValidationDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("FM Texture Validation Studio")
        self.resize(1450, 850)
        self.service = TextureValidationService()
        self.result: ValidationResult | None = None

        root = QVBoxLayout(self)
        title = QLabel("FM Texture Validation Studio")
        title.setObjectName("PageTitle")
        root.addWidget(title)
        summary = QLabel(
            "Inspect one refined donor texture, run transparent format and preservation checks, review regional metrics and create a reversible manual test package."
        )
        summary.setWordWrap(True)
        root.addWidget(summary)

        actions = QHBoxLayout()
        load = QPushButton("Load refined texture manifest")
        load.clicked.connect(self.load_manifest)
        self.save_report_button = QPushButton("Export validation report")
        self.save_report_button.setEnabled(False)
        self.save_report_button.clicked.connect(self.save_report)
        self.package_button = QPushButton("Create reversible test package")
        self.package_button.setEnabled(False)
        self.package_button.clicked.connect(self.create_package)
        actions.addWidget(load)
        actions.addWidget(self.save_report_button)
        actions.addWidget(self.package_button)
        actions.addStretch(1)
        root.addLayout(actions)

        previews = QHBoxLayout()
        self.donor_preview = self._preview("Donor texture")
        self.refined_preview = self._preview("Refined texture")
        self.heatmap_preview = self._preview("Difference heatmap")
        previews.addWidget(self.donor_preview, 1)
        previews.addWidget(self.refined_preview, 1)
        previews.addWidget(self.heatmap_preview, 1)
        root.addLayout(previews, 3)

        details = QHBoxLayout()
        self.checks = QTextEdit()
        self.checks.setReadOnly(True)
        self.checks.setPlaceholderText("Validation checks appear after loading a v2 refinement manifest")
        self.regions = QTextEdit()
        self.regions.setReadOnly(True)
        self.regions.setPlaceholderText("Regional coverage and difference metrics appear here")
        details.addWidget(self.checks, 1)
        details.addWidget(self.regions, 1)
        root.addLayout(details, 2)

        self.score = QLabel("No texture validated.")
        self.score.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.score.setWordWrap(True)
        root.addWidget(self.score)
        self.status = QLabel(
            "Validation is advisory. A passing report does not prove Football Manager match-engine compatibility."
        )
        self.status.setWordWrap(True)
        root.addWidget(self.status)

    @staticmethod
    def _preview(text: str) -> QScrollArea:
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setMinimumSize(360, 360)
        label.setObjectName("ValidationPreview")
        area = QScrollArea()
        area.setWidget(label)
        area.setWidgetResizable(True)
        area.preview_label = label  # type: ignore[attr-defined]
        return area

    def load_manifest(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(
            self, "Load refined texture manifest", "", "JSON files (*.json)"
        )
        if not selected:
            return
        try:
            self.result = self.service.validate(Path(selected))
        except ValueError as exc:
            QMessageBox.critical(self, "Validation failed", str(exc))
            self.result = None
            self.save_report_button.setEnabled(False)
            self.package_button.setEnabled(False)
            return
        self._show_image(self.donor_preview, Path(self.result.donor_texture))
        self._show_image(self.refined_preview, Path(self.result.refined_texture))
        self._show_qimage(self.heatmap_preview, self.result.heatmap)
        self.checks.setPlainText("\n".join(
            f"{'PASS' if check.passed else 'FAIL'}  {check.name}\n{check.detail}\n"
            for check in self.result.checks
        ))
        self.regions.setPlainText("\n".join(
            f"{region.name.replace('_', ' ').title()}\n"
            f"Average difference: {region.average_difference:.2f}\n"
            f"Changed coverage: {region.changed_coverage:.1%}\n"
            f"Confidence: {region.confidence:.1%}\n"
            for region in self.result.regions
        ))
        readiness = "READY FOR CONTROLLED TESTING" if self.result.ready_for_testing else "NOT READY — REVIEW FAILED CHECKS"
        self.score.setText(
            f"Advisory readiness score: {self.result.quality_score}%\n{readiness}\n"
            "This score checks internal consistency only; it is not an in-game quality guarantee."
        )
        self.save_report_button.setEnabled(True)
        self.package_button.setEnabled(self.result.ready_for_testing)
        self.status.setText(
            f"Validated donor {self.result.player_id} at {self.result.width}×{self.result.height}. "
            "Inspect the report and heatmap before creating a test package."
        )

    def save_report(self) -> None:
        if self.result is None:
            return
        selected, _ = QFileDialog.getSaveFileName(
            self, "Save validation report", f"facestudio-validation-{self.result.player_id}", "All files (*)"
        )
        if not selected:
            return
        try:
            paths = self.service.save_report(self.result, Path(selected))
        except OSError as exc:
            QMessageBox.critical(self, "Export failed", str(exc))
            return
        QMessageBox.information(self, "Validation report exported", "\n".join(str(path) for path in paths))

    def create_package(self) -> None:
        if self.result is None or not self.result.ready_for_testing:
            QMessageBox.warning(self, "Not ready", "Resolve failed validation checks before creating a test package.")
            return
        selected = QFileDialog.getExistingDirectory(self, "Choose test package destination")
        if not selected:
            return
        try:
            package = self.service.create_test_package(self.result, Path(selected))
        except OSError as exc:
            QMessageBox.critical(self, "Package failed", str(exc))
            return
        QMessageBox.information(
            self,
            "Reversible test package created",
            f"Created:\n{package}\n\nFootball Manager files were not modified automatically.",
        )

    @staticmethod
    def _show_image(area: QScrollArea, path: Path) -> None:
        pixmap = QPixmap(str(path))
        label = area.preview_label  # type: ignore[attr-defined]
        if pixmap.isNull():
            label.setText("Texture could not be decoded")
            return
        label.setText("")
        label.setPixmap(pixmap)
        label.adjustSize()

    @staticmethod
    def _show_qimage(area: QScrollArea, image) -> None:
        label = area.preview_label  # type: ignore[attr-defined]
        label.setText("")
        label.setPixmap(QPixmap.fromImage(image))
        label.adjustSize()

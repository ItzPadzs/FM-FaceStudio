from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QDialog, QFileDialog, QHBoxLayout, QLabel, QMessageBox, QPushButton, QSlider, QVBoxLayout

from facestudio.match_engine_research.texture_reconstruction import ReconstructionResult, TextureReconstructionService


class TextureReconstructionDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Triangulated Texture Reconstruction")
        self.resize(1100, 760)
        self.service = TextureReconstructionService()
        self.portrait_record: Path | None = None
        self.uv_record: Path | None = None
        self.result: ReconstructionResult | None = None

        root = QVBoxLayout(self)
        title = QLabel("FM26 Triangulated Texture Reconstruction")
        title.setObjectName("PageTitle")
        root.addWidget(title)
        description = QLabel(
            "Load the corrected portrait landmark JSON and the completed donor UV calibration JSON. "
            "FaceStudio maps matching facial triangles into the donor texture while preserving pixels outside the calibrated face region."
        )
        description.setWordWrap(True)
        root.addWidget(description)

        buttons = QHBoxLayout()
        portrait = QPushButton("Choose portrait landmark JSON")
        portrait.clicked.connect(self.choose_portrait)
        uv = QPushButton("Choose donor UV calibration JSON")
        uv.clicked.connect(self.choose_uv)
        buttons.addWidget(portrait); buttons.addWidget(uv)
        root.addLayout(buttons)

        self.record_status = QLabel("Portrait record: not selected\nUV calibration: not selected")
        self.record_status.setWordWrap(True)
        root.addWidget(self.record_status)

        opacity_row = QHBoxLayout()
        opacity_row.addWidget(QLabel("Feature transfer strength"))
        self.opacity = QSlider(Qt.Orientation.Horizontal)
        self.opacity.setRange(40, 100); self.opacity.setValue(92)
        self.opacity.valueChanged.connect(lambda value: self.opacity_label.setText(f"{value}%"))
        self.opacity_label = QLabel("92%")
        opacity_row.addWidget(self.opacity, 1); opacity_row.addWidget(self.opacity_label)
        root.addLayout(opacity_row)

        self.build_button = QPushButton("Build triangulated texture draft")
        self.build_button.setEnabled(False)
        self.build_button.clicked.connect(self.build)
        root.addWidget(self.build_button)

        previews = QHBoxLayout()
        self.donor_preview = self._preview("Donor texture")
        self.output_preview = self._preview("Reconstructed output")
        previews.addWidget(self.donor_preview, 1); previews.addWidget(self.output_preview, 1)
        root.addLayout(previews, 1)

        self.status = QLabel("Ready. Hair and facial-hair-dark pixels are excluded from the source transfer in this release.")
        self.status.setWordWrap(True)
        root.addWidget(self.status)
        self.export_button = QPushButton("Export reconstructed PNG and build manifest")
        self.export_button.setEnabled(False)
        self.export_button.clicked.connect(self.export)
        root.addWidget(self.export_button)

    @staticmethod
    def _preview(text: str) -> QLabel:
        label = QLabel(text); label.setAlignment(Qt.AlignmentFlag.AlignCenter); label.setMinimumSize(430, 430); label.setWordWrap(True)
        return label

    def choose_portrait(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(self, "Choose corrected portrait record", "", "JSON files (*.json)")
        if selected: self.portrait_record = Path(selected); self.refresh_state()

    def choose_uv(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(self, "Choose completed donor UV calibration", "", "JSON files (*.json)")
        if selected: self.uv_record = Path(selected); self.refresh_state()

    def refresh_state(self) -> None:
        self.record_status.setText(
            f"Portrait record: {self.portrait_record or 'not selected'}\nUV calibration: {self.uv_record or 'not selected'}"
        )
        self.build_button.setEnabled(self.portrait_record is not None and self.uv_record is not None)
        self.result = None; self.export_button.setEnabled(False)

    def build(self) -> None:
        if self.portrait_record is None or self.uv_record is None: return
        try:
            self.result = self.service.reconstruct(self.portrait_record, self.uv_record, self.opacity.value()/100)
        except ValueError as exc:
            QMessageBox.critical(self, "Reconstruction failed", str(exc)); return
        donor = QPixmap(self.result.donor_texture)
        self.donor_preview.setPixmap(donor.scaled(self.donor_preview.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        output = QPixmap.fromImage(self.result.output)
        self.output_preview.setPixmap(output.scaled(self.output_preview.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.export_button.setEnabled(True)
        self.status.setText(
            f"Built donor {self.result.player_id}: {self.result.triangles_written} triangles, "
            f"{self.result.pixels_written} transferred pixels and {self.result.skipped_hair_pixels} excluded dark hair/facial-hair pixels."
        )

    def export(self) -> None:
        if self.result is None: return
        selected, _ = QFileDialog.getSaveFileName(self, "Export reconstructed texture", f"{self.result.player_id}-reconstructed.png", "PNG files (*.png)")
        if not selected: return
        try: png, manifest = self.service.save(self.result, Path(selected))
        except OSError as exc: QMessageBox.critical(self, "Export failed", str(exc)); return
        QMessageBox.information(self, "Reconstruction exported", f"Texture:\n{png}\n\nManifest:\n{manifest}")

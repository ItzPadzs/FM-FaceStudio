from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog, QFileDialog, QFormLayout, QHBoxLayout, QLabel, QMessageBox,
    QPushButton, QSlider, QVBoxLayout,
)

from facestudio.match_engine_research.texture_refinement import (
    RefinementResult, RefinementSettings, TextureRefinementService,
)


class TextureRefinementDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Texture Refinement Pipeline")
        self.resize(1100, 720)
        self.service = TextureRefinementService()
        self.manifest: Path | None = None
        self.result: RefinementResult | None = None

        root = QVBoxLayout(self)
        root.addWidget(QLabel("Refine triangle seams, equalise colour, smooth neighbours and repair small reconstruction gaps."))
        choose = QPushButton("Load reconstruction manifest")
        choose.clicked.connect(self.choose_manifest)
        root.addWidget(choose)
        self.record_status = QLabel("No facestudio-texture-reconstruction-v1 manifest loaded.")
        self.record_status.setWordWrap(True)
        root.addWidget(self.record_status)

        controls = QFormLayout()
        self.feather = self._slider(0, 20, 6)
        self.colour = self._slider(0, 100, 65)
        self.blend = self._slider(0, 100, 35)
        controls.addRow("Edge feather (px)", self.feather)
        controls.addRow("Colour matching (%)", self.colour)
        controls.addRow("Neighbour blend (%)", self.blend)
        root.addLayout(controls)

        previews = QHBoxLayout()
        self.donor_preview = self._preview("Donor texture")
        self.raw_preview = self._preview("Raw reconstruction")
        self.refined_preview = self._preview("Refined reconstruction")
        previews.addWidget(self.donor_preview, 1)
        previews.addWidget(self.raw_preview, 1)
        previews.addWidget(self.refined_preview, 1)
        root.addLayout(previews, 1)

        actions = QHBoxLayout()
        build = QPushButton("Build refined preview")
        build.clicked.connect(self.build)
        self.export = QPushButton("Export refined PNG and manifest")
        self.export.setEnabled(False)
        self.export.clicked.connect(self.save)
        actions.addWidget(build)
        actions.addWidget(self.export)
        root.addLayout(actions)
        self.status = QLabel("Ready. Refinement preserves every donor pixel outside the reconstructed facial mask.")
        self.status.setWordWrap(True)
        root.addWidget(self.status)

    @staticmethod
    def _slider(low: int, high: int, value: int) -> QSlider:
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(low, high); slider.setValue(value); slider.setTickInterval(5)
        return slider

    @staticmethod
    def _preview(text: str) -> QLabel:
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setMinimumSize(280, 360)
        label.setWordWrap(True)
        return label

    def choose_manifest(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(self, "Load reconstruction manifest", "", "JSON files (*.json)")
        if not selected: return
        self.manifest = Path(selected)
        self.result = None; self.export.setEnabled(False)
        self.record_status.setText(str(self.manifest))
        self.status.setText("Manifest selected. Build a refined preview with the current controls.")

    def build(self) -> None:
        if self.manifest is None:
            QMessageBox.warning(self, "Manifest required", "Load a reconstruction manifest first."); return
        settings = RefinementSettings(self.feather.value(), self.colour.value()/100.0, self.blend.value()/100.0)
        try:
            self.result = self.service.refine(self.manifest, settings)
        except ValueError as exc:
            QMessageBox.critical(self, "Refinement failed", str(exc)); return
        self._show(self.donor_preview, self.result.donor_texture)
        self._show(self.raw_preview, self.result.raw_texture)
        self.refined_preview.setPixmap(QPixmap.fromImage(self.result.output).scaled(self.refined_preview.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.export.setEnabled(True)
        self.status.setText(
            f"Refined {self.result.changed_pixels} facial pixels; feathered {self.result.feathered_pixels}; "
            f"colour-adjusted {self.result.colour_adjusted_pixels}; repaired {self.result.gap_repairs} small gaps."
        )

    @staticmethod
    def _show(label: QLabel, path: str) -> None:
        pixmap = QPixmap(path)
        label.setPixmap(pixmap.scaled(label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def save(self) -> None:
        if self.result is None:
            QMessageBox.warning(self, "Nothing to export", "Build the refined preview first."); return
        selected, _ = QFileDialog.getSaveFileName(self, "Export refined texture", f"facestudio-refined-{self.result.player_id}.png", "PNG files (*.png)")
        if not selected: return
        try:
            png, manifest = self.service.save(self.result, Path(selected))
        except OSError as exc:
            QMessageBox.critical(self, "Export failed", str(exc)); return
        QMessageBox.information(self, "Refinement exported", f"Texture:\n{png}\n\nManifest:\n{manifest}")

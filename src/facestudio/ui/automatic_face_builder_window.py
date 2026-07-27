from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QDoubleSpinBox, QFileDialog, QFormLayout,
    QFrame, QHBoxLayout, QLabel, QMainWindow, QMessageBox, QProgressBar,
    QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from facestudio.match_engine_research.automatic_calibration import AutomaticCalibrationService
from facestudio.match_engine_research.automatic_face_builder import (
    AutomaticBuildInputs, AutomaticBuildResult, AutomaticFaceBuilderService,
)
from facestudio.match_engine_research.integrated_face_builder import IntegratedBuildInputs, IntegratedFaceBuilderService
from facestudio.ui.integrated_face_builder_window import IntegratedFaceBuilderWindow
from facestudio.ui.theme import DARK_STYLESHEET, LIGHT_STYLESHEET
from facestudio.utils.config import AppConfig


class CalibrationEditorDialog(QDialog):
    """Fine tune generated normalised landmark or UV anchor coordinates."""

    def __init__(self, record: Path, mode: str, parent=None) -> None:
        super().__init__(parent)
        self.record = record; self.mode = mode
        self.payload = json.loads(record.read_text(encoding="utf-8"))
        self.points = self.payload["landmarks" if mode == "geometry" else "anchors"]
        self.setWindowTitle("Fine Tune Geometry" if mode == "geometry" else "Fine Tune UV Profile")
        self.resize(620, 560)
        layout = QVBoxLayout(self)
        note = QLabel("Adjust X and Y between 0 and 1. Changes are saved as reviewed corrections; rebuild afterwards to apply them.")
        note.setWordWrap(True); layout.addWidget(note)
        self.table = QTableWidget(len(self.points), 3); self.table.setHorizontalHeaderLabels(["Point", "X", "Y"])
        for row, point in enumerate(self.points):
            self.table.setItem(row, 0, QTableWidgetItem(str(point["name"])))
            for column, field in ((1, "x"), (2, "y")):
                spin = QDoubleSpinBox(); spin.setRange(0.0, 1.0); spin.setDecimals(4); spin.setSingleStep(0.005)
                spin.setValue(float(point[field])); self.table.setCellWidget(row, column, spin)
        self.table.horizontalHeader().setStretchLastSection(True); layout.addWidget(self.table, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.save); buttons.rejected.connect(self.reject); layout.addWidget(buttons)

    def save(self) -> None:
        updates = {str(point["name"]): (self.table.cellWidget(row, 1).value(), self.table.cellWidget(row, 2).value()) for row, point in enumerate(self.points)}
        service = AutomaticCalibrationService()
        service.update_geometry(self.record, updates) if self.mode == "geometry" else service.update_uv(self.record, updates)
        self.accept()


class AutomaticFaceBuilderWindow(QMainWindow):
    """Photo-first build with generated, editable geometry and UV calibration."""

    def __init__(self, config: AppConfig, config_path: Path) -> None:
        super().__init__()
        self.config = config; self.config_path = config_path; self.service = AutomaticFaceBuilderService()
        self.photo: Path | None = None; self.dataset: Path | None = None; self.assets: Path | None = None
        self.profiles: Path | None = None; self.workspace: Path | None = None; self.last_result: AutomaticBuildResult | None = None
        self.advanced: IntegratedFaceBuilderWindow | None = None
        self.setWindowTitle("FM FaceStudio — Alpha 8.3.0 — Auto Calibration & Fine Tuning")
        self.resize(1440, 900); self.setMinimumSize(1040, 700)
        self.setStyleSheet(LIGHT_STYLESHEET if config.theme == "light" else DARK_STYLESHEET); self._build_ui()

    def _build_ui(self) -> None:
        root = QWidget(); self.setCentralWidget(root)
        outer = QHBoxLayout(root); outer.setContentsMargins(0, 0, 0, 0); outer.setSpacing(0)
        side = QFrame(); side.setObjectName("Sidebar"); side.setFixedWidth(250)
        sl = QVBoxLayout(side); sl.setContentsMargins(18, 24, 18, 20)
        brand = QLabel("FM FaceStudio"); brand.setObjectName("Brand"); sl.addWidget(brand)
        version = QLabel("ALPHA 8.3.0\nAUTO CALIBRATION"); version.setObjectName("Muted"); sl.addWidget(version); sl.addSpacing(20)
        quick = QPushButton("✦  Quick Build"); quick.setCheckable(True); quick.setChecked(True); sl.addWidget(quick)
        advanced = QPushButton("Advanced Workspace"); advanced.clicked.connect(self.open_advanced); sl.addWidget(advanced); sl.addStretch()
        note = QLabel("Upload one photo. FaceStudio estimates geometry, selects a donor, creates or reuses a UV profile, then builds. Generated calibration remains editable.")
        note.setWordWrap(True); note.setObjectName("Muted"); sl.addWidget(note); outer.addWidget(side)

        page = QWidget(); layout = QVBoxLayout(page); layout.setContentsMargins(30, 26, 30, 26); layout.setSpacing(15)
        title = QLabel("Build and Calibrate From One Photograph"); title.setStyleSheet("font-size: 31px; font-weight: 700;")
        subtitle = QLabel("Automatic estimates get you to a result quickly. Fine tune geometry or UV anchors only when the preview needs improvement.")
        subtitle.setWordWrap(True); subtitle.setObjectName("Muted"); layout.addWidget(title); layout.addWidget(subtitle)
        setup = QFrame(); setup.setObjectName("Card"); form = QFormLayout(setup)
        self.photo_label = QLabel("No photograph selected"); self.dataset_label = QLabel("No calibrated geometry dataset selected")
        self.assets_label = QLabel("No donor texture folder selected"); self.profile_label = QLabel("Profiles will be created inside the output folder")
        self.output_label = QLabel("No output folder selected")
        for label in (self.photo_label, self.dataset_label, self.assets_label, self.profile_label, self.output_label):
            label.setWordWrap(True); label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        form.addRow("Photograph", self._row(self.photo_label, self._button("Upload Photograph", self.choose_photo)))
        form.addRow("Geometry library", self._row(self.dataset_label, self._button("Choose Geometry Dataset", self.choose_dataset)))
        form.addRow("Donor textures", self._row(self.assets_label, self._button("Choose Donor Asset Folder", self.choose_assets)))
        form.addRow("UV profiles", self._row(self.profile_label, self._button("Optional Profile Folder", self.choose_profiles)))
        form.addRow("Output", self._row(self.output_label, self._button("Choose Output Folder", self.choose_workspace))); layout.addWidget(setup)
        content = QHBoxLayout(); self.preview = self._preview_card(content, "Your Photograph", "Upload one clear front-facing photograph")
        self.result_preview = self._preview_card(content, "Automatic Result", "The refined donor texture will appear here"); layout.addLayout(content, 1)
        self.progress = QProgressBar(); self.progress.setRange(0, 100); layout.addWidget(self.progress)
        self.status = QLabel("Ready for a photograph."); self.status.setWordWrap(True); layout.addWidget(self.status)
        actions = QHBoxLayout(); self.build_button = QPushButton("✦  Build Face Automatically"); self.build_button.setMinimumHeight(48); self.build_button.clicked.connect(self.build)
        self.geometry_button = QPushButton("Fine Tune Geometry"); self.geometry_button.setEnabled(False); self.geometry_button.clicked.connect(self.tune_geometry)
        self.uv_button = QPushButton("Fine Tune UV Profile"); self.uv_button.setEnabled(False); self.uv_button.clicked.connect(self.tune_uv)
        self.rebuild_button = QPushButton("Rebuild With Changes"); self.rebuild_button.setEnabled(False); self.rebuild_button.clicked.connect(self.rebuild_changed)
        actions.addWidget(self.build_button, 1); actions.addWidget(self.geometry_button); actions.addWidget(self.uv_button); actions.addWidget(self.rebuild_button); layout.addLayout(actions)
        boundary = QLabel("Generated geometry and UV profiles are provisional editable estimates. They do not decode .skin meshes or guarantee match-engine compatibility.")
        boundary.setWordWrap(True); boundary.setObjectName("Muted"); layout.addWidget(boundary); outer.addWidget(page, 1)

    @staticmethod
    def _button(text, callback):
        button = QPushButton(text); button.clicked.connect(callback); return button

    @staticmethod
    def _row(label: QLabel, button: QPushButton) -> QWidget:
        widget = QWidget(); row = QHBoxLayout(widget); row.setContentsMargins(0, 0, 0, 0); row.addWidget(label, 1); row.addWidget(button); return widget

    @staticmethod
    def _preview_card(content: QHBoxLayout, title: str, empty: str) -> QLabel:
        card = QFrame(); card.setObjectName("Card"); box = QVBoxLayout(card); box.addWidget(QLabel(title))
        preview = QLabel(empty); preview.setAlignment(Qt.AlignmentFlag.AlignCenter); preview.setMinimumHeight(430)
        preview.setStyleSheet("border: 1px solid #34404c; border-radius: 6px;"); box.addWidget(preview, 1); content.addWidget(card, 1); return preview

    def choose_photo(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(self, "Choose photograph", "", "Images (*.png *.jpg *.jpeg *.webp *.bmp)")
        if filename: self.photo = Path(filename); self.photo_label.setText(filename); self._set_preview(self.preview, filename)

    def choose_dataset(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(self, "Calibrated geometry dataset", "", "FaceStudio JSON (*.json)")
        if filename: self.dataset = Path(filename); self.dataset_label.setText(filename)

    def choose_assets(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Donor textures and assets")
        if folder: self.assets = Path(folder); self.assets_label.setText(folder)

    def choose_profiles(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Reusable UV profile folder")
        if folder: self.profiles = Path(folder); self.profile_label.setText(folder)

    def choose_workspace(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Automatic build output")
        if folder: self.workspace = Path(folder); self.output_label.setText(folder)

    def build(self) -> None:
        if not all((self.photo, self.dataset, self.assets, self.workspace)):
            QMessageBox.information(self, "Quick build setup", "Choose the photograph, geometry dataset, donor asset folder and output folder first."); return
        self.build_button.setEnabled(False); self.progress.setValue(10); self.status.setText("Estimating portrait landmarks and geometry…")
        try:
            self.progress.setValue(35); self.status.setText("Ranking donors and generating or reusing a UV profile…")
            result = self.service.build(AutomaticBuildInputs(self.photo, self.dataset, self.assets, self.workspace, self.profiles)); self.last_result = result
            self._show_result(result, "generated automatically" if result.generated_uv_profile else "reused")
            self.geometry_button.setEnabled(True); self.uv_button.setEnabled(True); self.rebuild_button.setEnabled(True)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            self.progress.setValue(0); self.status.setText("Automatic build stopped. Check the selected resources or open Advanced Workspace."); QMessageBox.critical(self, "Automatic build failed", str(exc))
        finally: self.build_button.setEnabled(True)

    def rebuild_changed(self) -> None:
        if not self.last_result or not self.workspace: return
        self.rebuild_button.setEnabled(False); self.progress.setValue(35); self.status.setText("Rebuilding with fine-tuned geometry and UV anchors…")
        try:
            integrated = IntegratedFaceBuilderService().build(IntegratedBuildInputs(self.last_result.portrait_record, self.last_result.uv_record, self.workspace))
            self.progress.setValue(100); validation = integrated.validation_result
            self.status.setText(f"Fine-tuned rebuild complete. Validation: {validation.quality_score}%. The generated calibration files were preserved.")
            self._set_preview(self.result_preview, validation.refined_texture)
        except (OSError, ValueError) as exc:
            self.progress.setValue(0); QMessageBox.critical(self, "Rebuild failed", str(exc))
        finally: self.rebuild_button.setEnabled(True)

    def _show_result(self, result: AutomaticBuildResult, uv_text: str) -> None:
        self.progress.setValue(100); validation = result.integrated.validation_result
        self.status.setText(f"Build complete. Donor {result.selected_match.player_id} selected at {result.selected_match.score}% geometry score. UV profile {uv_text}. Validation: {validation.quality_score}%. Fine tune either calibration and rebuild when needed.")
        self._set_preview(self.result_preview, validation.refined_texture)

    def tune_geometry(self) -> None:
        if self.last_result and CalibrationEditorDialog(self.last_result.geometry_record, "geometry", self).exec(): self.status.setText("Geometry fine tuning saved. Press Rebuild With Changes to apply it.")

    def tune_uv(self) -> None:
        if self.last_result and CalibrationEditorDialog(self.last_result.uv_record, "uv", self).exec(): self.status.setText("UV fine tuning saved. Press Rebuild With Changes to apply it.")

    @staticmethod
    def _set_preview(label: QLabel, path) -> None:
        pixmap = QPixmap(str(path))
        if not pixmap.isNull(): label.setPixmap(pixmap.scaled(560, 490, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def open_advanced(self) -> None:
        self.advanced = IntegratedFaceBuilderWindow(self.config, self.config_path); self.advanced.show()

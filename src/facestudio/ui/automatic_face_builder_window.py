from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFileDialog, QFormLayout, QFrame, QHBoxLayout, QLabel, QMainWindow,
    QMessageBox, QProgressBar, QPushButton, QVBoxLayout, QWidget,
)

from facestudio.match_engine_research.automatic_face_builder import (
    AutomaticBuildInputs, AutomaticFaceBuilderService,
)
from facestudio.ui.integrated_face_builder_window import IntegratedFaceBuilderWindow
from facestudio.ui.theme import DARK_STYLESHEET, LIGHT_STYLESHEET
from facestudio.utils.config import AppConfig


class AutomaticFaceBuilderWindow(QMainWindow):
    """Photo-first build surface with advanced workflow available when review is needed."""

    def __init__(self, config: AppConfig, config_path: Path) -> None:
        super().__init__()
        self.config = config
        self.config_path = config_path
        self.service = AutomaticFaceBuilderService()
        self.photo: Path | None = None
        self.dataset: Path | None = None
        self.profiles: Path | None = None
        self.workspace: Path | None = None
        self.advanced: IntegratedFaceBuilderWindow | None = None
        self.setWindowTitle("FM FaceStudio — Alpha 8.2.0 — Automatic Quick Build")
        self.resize(1420, 880)
        self.setMinimumSize(1040, 680)
        self.setStyleSheet(LIGHT_STYLESHEET if config.theme == "light" else DARK_STYLESHEET)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QWidget(); self.setCentralWidget(root)
        outer = QHBoxLayout(root); outer.setContentsMargins(0, 0, 0, 0); outer.setSpacing(0)
        side = QFrame(); side.setObjectName("Sidebar"); side.setFixedWidth(245)
        sl = QVBoxLayout(side); sl.setContentsMargins(18, 24, 18, 20)
        brand = QLabel("FM FaceStudio"); brand.setObjectName("Brand"); sl.addWidget(brand)
        version = QLabel("ALPHA 8.2.0\nAUTOMATIC QUICK BUILD"); version.setObjectName("Muted"); sl.addWidget(version)
        sl.addSpacing(20)
        quick = QPushButton("✦  Quick Build"); quick.setCheckable(True); quick.setChecked(True); sl.addWidget(quick)
        advanced = QPushButton("Advanced Workspace"); advanced.clicked.connect(self.open_advanced); sl.addWidget(advanced)
        sl.addStretch()
        note = QLabel("Choose one photograph. FaceStudio analyses it, ranks calibrated donors, finds a reviewed UV profile, reconstructs, refines and validates automatically.")
        note.setWordWrap(True); note.setObjectName("Muted"); sl.addWidget(note)
        outer.addWidget(side)

        page = QWidget(); layout = QVBoxLayout(page); layout.setContentsMargins(30, 26, 30, 26); layout.setSpacing(16)
        title = QLabel("Build a Face From One Photograph"); title.setStyleSheet("font-size: 31px; font-weight: 700;")
        subtitle = QLabel("Upload the photograph and press Build Face. Resource locations only need configuring when they change.")
        subtitle.setWordWrap(True); subtitle.setObjectName("Muted")
        layout.addWidget(title); layout.addWidget(subtitle)

        setup = QFrame(); setup.setObjectName("Card"); form = QFormLayout(setup)
        self.photo_label = QLabel("No photograph selected")
        self.dataset_label = QLabel("No calibrated geometry dataset selected")
        self.profile_label = QLabel("No reviewed UV profile folder selected")
        self.output_label = QLabel("No output folder selected")
        for label in (self.photo_label, self.dataset_label, self.profile_label, self.output_label):
            label.setWordWrap(True); label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        photo_btn = QPushButton("Upload Photograph"); photo_btn.clicked.connect(self.choose_photo)
        dataset_btn = QPushButton("Choose Geometry Dataset"); dataset_btn.clicked.connect(self.choose_dataset)
        profile_btn = QPushButton("Choose UV Profile Folder"); profile_btn.clicked.connect(self.choose_profiles)
        output_btn = QPushButton("Choose Output Folder"); output_btn.clicked.connect(self.choose_workspace)
        form.addRow("Photograph", self._row(self.photo_label, photo_btn))
        form.addRow("Geometry library", self._row(self.dataset_label, dataset_btn))
        form.addRow("UV profiles", self._row(self.profile_label, profile_btn))
        form.addRow("Output", self._row(self.output_label, output_btn))
        layout.addWidget(setup)

        content = QHBoxLayout()
        preview_card = QFrame(); preview_card.setObjectName("Card"); pv = QVBoxLayout(preview_card)
        pv.addWidget(QLabel("Your Photograph"))
        self.preview = QLabel("Upload one clear front-facing photograph")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter); self.preview.setMinimumHeight(440)
        self.preview.setStyleSheet("border: 1px solid #34404c; border-radius: 6px;")
        pv.addWidget(self.preview, 1); content.addWidget(preview_card, 1)
        result_card = QFrame(); result_card.setObjectName("Card"); rv = QVBoxLayout(result_card)
        rv.addWidget(QLabel("Automatic Result"))
        self.result_preview = QLabel("The refined donor texture will appear here")
        self.result_preview.setAlignment(Qt.AlignmentFlag.AlignCenter); self.result_preview.setMinimumHeight(440)
        self.result_preview.setStyleSheet("border: 1px solid #34404c; border-radius: 6px;")
        rv.addWidget(self.result_preview, 1); content.addWidget(result_card, 1)
        layout.addLayout(content, 1)

        self.progress = QProgressBar(); self.progress.setRange(0, 100); self.progress.setValue(0); layout.addWidget(self.progress)
        self.status = QLabel("Ready for a photograph."); self.status.setWordWrap(True); layout.addWidget(self.status)
        self.build_button = QPushButton("✦  Build Face Automatically"); self.build_button.setMinimumHeight(48)
        self.build_button.clicked.connect(self.build); layout.addWidget(self.build_button)
        boundary = QLabel("Automatic landmarks are initial estimates. Donor matching uses calibrated geometry and only completed reviewed UV profiles. The result remains a reversible texture test, not generated .skin geometry.")
        boundary.setWordWrap(True); boundary.setObjectName("Muted"); layout.addWidget(boundary)
        outer.addWidget(page, 1)

    @staticmethod
    def _row(label: QLabel, button: QPushButton) -> QWidget:
        widget = QWidget(); row = QHBoxLayout(widget); row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(label, 1); row.addWidget(button); return widget

    def choose_photo(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(self, "Choose photograph", "", "Images (*.png *.jpg *.jpeg *.webp *.bmp)")
        if not filename: return
        self.photo = Path(filename); self.photo_label.setText(filename)
        pixmap = QPixmap(filename)
        if not pixmap.isNull():
            self.preview.setPixmap(pixmap.scaled(560, 500, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def choose_dataset(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(self, "Calibrated geometry dataset", "", "FaceStudio JSON (*.json)")
        if filename: self.dataset = Path(filename); self.dataset_label.setText(filename)

    def choose_profiles(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Reviewed donor UV profiles")
        if folder: self.profiles = Path(folder); self.profile_label.setText(folder)

    def choose_workspace(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Automatic build output")
        if folder: self.workspace = Path(folder); self.output_label.setText(folder)

    def build(self) -> None:
        if not all((self.photo, self.dataset, self.profiles, self.workspace)):
            QMessageBox.information(self, "Quick build setup", "Choose the photograph, geometry dataset, UV profile folder and output folder first.")
            return
        self.build_button.setEnabled(False); self.progress.setValue(10); self.status.setText("Analysing photograph and estimating landmarks…")
        try:
            self.progress.setValue(30); self.status.setText("Matching against calibrated donor geometry and locating a reviewed UV profile…")
            result = self.service.build(AutomaticBuildInputs(self.photo, self.dataset, self.profiles, self.workspace))
            self.progress.setValue(100)
            validation = result.integrated.validation_result
            self.status.setText(
                f"Build complete. Donor {result.selected_match.player_id} selected at {result.selected_match.score}% geometry score. "
                f"Validation: {validation.quality_score}%. "
                + ("Ready for controlled testing." if validation.ready_for_testing else "Review the result before testing.")
            )
            pixmap = QPixmap(validation.refined_texture)
            if not pixmap.isNull():
                self.result_preview.setPixmap(pixmap.scaled(560, 500, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        except (OSError, ValueError) as exc:
            self.progress.setValue(0); self.status.setText("Automatic build stopped. Open Advanced Workspace when a reviewed prerequisite needs attention.")
            QMessageBox.critical(self, "Automatic build failed", str(exc))
        finally:
            self.build_button.setEnabled(True)

    def open_advanced(self) -> None:
        self.advanced = IntegratedFaceBuilderWindow(self.config, self.config_path)
        self.advanced.show()

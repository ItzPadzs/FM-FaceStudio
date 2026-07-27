from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFileDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QMainWindow,
    QMessageBox, QProgressBar, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from facestudio.match_engine_research.integrated_face_builder import (
    IntegratedBuildInputs, IntegratedFaceBuilderService,
)
from facestudio.ui.theme import DARK_STYLESHEET, LIGHT_STYLESHEET
from facestudio.utils.config import AppConfig


class IntegratedFaceBuilderWindow(QMainWindow):
    """Single-window integration of the reviewed FaceStudio texture pipeline."""

    def __init__(self, config: AppConfig, config_path: Path) -> None:
        super().__init__()
        self.config = config
        self.config_path = config_path
        self.service = IntegratedFaceBuilderService()
        self.portrait_record: Path | None = None
        self.uv_record: Path | None = None
        self.workspace: Path | None = None
        self.setWindowTitle("FM FaceStudio — Alpha 8.0.0 — Integrated Face Builder")
        self.resize(1480, 900)
        self.setMinimumSize(1100, 700)
        self.setStyleSheet(LIGHT_STYLESHEET if config.theme == "light" else DARK_STYLESHEET)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QWidget(); self.setCentralWidget(root)
        outer = QHBoxLayout(root); outer.setContentsMargins(0, 0, 0, 0); outer.setSpacing(0)

        side = QFrame(); side.setObjectName("Sidebar"); side.setFixedWidth(230)
        sl = QVBoxLayout(side); sl.setContentsMargins(18, 24, 18, 20)
        brand = QLabel("FM FaceStudio"); brand.setObjectName("Brand"); sl.addWidget(brand)
        version = QLabel("ALPHA 8.0.0\nINTEGRATED FACE BUILDER"); version.setObjectName("Muted"); sl.addWidget(version)
        sl.addSpacing(24)
        nav = QPushButton("✦  Build Face"); nav.setCheckable(True); nav.setChecked(True); sl.addWidget(nav)
        sl.addStretch()
        boundary = QLabel(
            "CURRENT PIPELINE\n\n1. Reviewed portrait landmarks\n2. Reviewed donor UV anchors\n3. Reconstruct texture\n4. Refine and validate\n5. Export reversible package"
        )
        boundary.setWordWrap(True); boundary.setObjectName("Muted"); sl.addWidget(boundary)
        outer.addWidget(side)

        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget(); scroll.setWidget(content); outer.addWidget(scroll, 1)
        page = QVBoxLayout(content); page.setContentsMargins(26, 22, 26, 24); page.setSpacing(16)

        header = QHBoxLayout()
        titlebox = QVBoxLayout()
        title = QLabel("Build One Reviewed FM Face"); title.setStyleSheet("font-size: 30px; font-weight: 700;")
        subtitle = QLabel("Run reconstruction, refinement, validation and reversible packaging in one traceable workflow.")
        subtitle.setWordWrap(True); subtitle.setObjectName("Muted")
        titlebox.addWidget(title); titlebox.addWidget(subtitle); header.addLayout(titlebox, 1)
        self.build_button = QPushButton("✦  Build Face"); self.build_button.setMinimumSize(150, 42)
        self.build_button.clicked.connect(self.build); header.addWidget(self.build_button)
        page.addLayout(header)

        prereq = QFrame(); prereq.setObjectName("Card")
        pg = QGridLayout(prereq); pg.setContentsMargins(14, 12, 14, 12)
        self.portrait_path = QLabel("No corrected portrait landmark record selected")
        self.uv_path = QLabel("No completed donor UV calibration selected")
        self.output_path = QLabel("No output workspace selected")
        for label in (self.portrait_path, self.uv_path, self.output_path): label.setObjectName("Muted"); label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        pbtn = QPushButton("Choose Portrait JSON"); pbtn.clicked.connect(self.choose_portrait)
        ubtn = QPushButton("Choose Donor UV JSON"); ubtn.clicked.connect(self.choose_uv)
        obtn = QPushButton("Choose Output Folder"); obtn.clicked.connect(self.choose_workspace)
        pg.addWidget(self.portrait_path, 0, 0); pg.addWidget(pbtn, 0, 1)
        pg.addWidget(self.uv_path, 1, 0); pg.addWidget(ubtn, 1, 1)
        pg.addWidget(self.output_path, 2, 0); pg.addWidget(obtn, 2, 1)
        page.addWidget(prereq)

        cards = QHBoxLayout(); cards.setSpacing(12)
        self.photo_preview, photo_card = self._preview_card("1. Reviewed Photograph")
        self.donor_preview, donor_card = self._preview_card("2. Reviewed Donor UV")
        self.result_preview, result_card = self._preview_card("3. Refined Texture")
        cards.addWidget(photo_card, 1); cards.addWidget(donor_card, 1); cards.addWidget(result_card, 1)
        page.addLayout(cards, 1)

        status_card = QFrame(); status_card.setObjectName("Card")
        sv = QVBoxLayout(status_card); sv.setContentsMargins(16, 14, 16, 14)
        self.progress = QProgressBar(); self.progress.setRange(0, 4); self.progress.setValue(0)
        self.stage = QLabel("Select the two reviewed records and an output folder.")
        self.stage.setWordWrap(True)
        self.score = QLabel("Validation score: —"); self.score.setStyleSheet("font-size: 18px; font-weight: 600;")
        self.disclaimer = QLabel("This integrates the texture workflow for an existing donor head. It does not create or decode .skin geometry and does not modify Football Manager automatically.")
        self.disclaimer.setWordWrap(True); self.disclaimer.setObjectName("Muted")
        sv.addWidget(self.progress); sv.addWidget(self.stage); sv.addWidget(self.score); sv.addWidget(self.disclaimer)
        page.addWidget(status_card)

    @staticmethod
    def _preview_card(title: str) -> tuple[QLabel, QFrame]:
        card = QFrame(); card.setObjectName("Card")
        layout = QVBoxLayout(card); layout.setContentsMargins(12, 12, 12, 12)
        heading = QLabel(title); heading.setStyleSheet("font-weight: 650; font-size: 16px;")
        preview = QLabel("Awaiting input"); preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview.setMinimumHeight(360); preview.setStyleSheet("border: 1px solid #34404c; border-radius: 6px;")
        layout.addWidget(heading); layout.addWidget(preview, 1)
        return preview, card

    def choose_portrait(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(self, "Corrected portrait landmarks", "", "FaceStudio JSON (*.json)")
        if not filename: return
        self.portrait_record = Path(filename); self.portrait_path.setText(filename)
        self._load_record_preview(self.portrait_record, "source_path", self.photo_preview)

    def choose_uv(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(self, "Completed donor UV calibration", "", "FaceStudio JSON (*.json)")
        if not filename: return
        self.uv_record = Path(filename); self.uv_path.setText(filename)
        self._load_record_preview(self.uv_record, "texture_path", self.donor_preview)

    def choose_workspace(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Integrated build output")
        if folder: self.workspace = Path(folder); self.output_path.setText(folder)

    @staticmethod
    def _load_record_preview(record: Path, field: str, label: QLabel) -> None:
        try:
            payload = json.loads(record.read_text(encoding="utf-8")); image = Path(str(payload[field])).expanduser()
            pixmap = QPixmap(str(image))
            if pixmap.isNull(): raise ValueError("image could not be decoded")
            label.setPixmap(pixmap.scaled(420, 420, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        except (OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
            label.setText(f"Preview unavailable\n{exc}")

    def build(self) -> None:
        if not self.portrait_record or not self.uv_record or not self.workspace:
            QMessageBox.information(self, "Build prerequisites", "Choose the corrected portrait JSON, completed donor UV JSON and output folder first.")
            return
        self.build_button.setEnabled(False); self.progress.setValue(1); self.stage.setText("Reconstructing reviewed facial regions…")
        try:
            result = self.service.build(IntegratedBuildInputs(self.portrait_record, self.uv_record, self.workspace))
            self.progress.setValue(4)
            self.score.setText(f"Validation score: {result.validation_result.quality_score}%")
            if result.package_directory:
                self.stage.setText(f"Build complete and ready for controlled testing.\nPackage: {result.package_directory}")
            else:
                self.stage.setText("Build complete, but validation did not reach the controlled-test threshold. Review the exported reports.")
            pixmap = QPixmap(result.validation_result.refined_texture)
            if not pixmap.isNull():
                self.result_preview.setPixmap(pixmap.scaled(420, 420, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        except (OSError, ValueError) as exc:
            self.progress.setValue(0); self.stage.setText("Build stopped. Correct the reported prerequisite or validation issue.")
            QMessageBox.critical(self, "Integrated build failed", str(exc))
        finally:
            self.build_button.setEnabled(True)

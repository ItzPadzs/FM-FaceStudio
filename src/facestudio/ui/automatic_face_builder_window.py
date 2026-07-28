from __future__ import annotations

from pathlib import Path
import traceback

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QFrame, QHBoxLayout, QLabel, QMainWindow,
    QMessageBox, QProgressBar, QPushButton, QVBoxLayout, QWidget,
)

from facestudio.texture_generator import HeadTextureGenerator, TextureBuildResult
from facestudio.ui.theme import DARK_STYLESHEET, LIGHT_STYLESHEET
from facestudio.utils.config import AppConfig


class AutomaticFaceBuilderWindow(QMainWindow):
    """One-photo workflow with automatic launch and live pipeline feedback."""

    STAGES = (
        (12, "Face detection", "Detecting and centring the face…"),
        (28, "Alignment", "Aligning the portrait to the FM face region…"),
        (48, "Identity encoding", "Preparing facial identity and skin detail…"),
        (68, "FM UV estimation", "Estimating the FM head-texture layout…"),
        (84, "Texture generation", "Generating the head texture…"),
        (94, "Post-processing", "Blending seams and finishing the PNG…"),
    )

    def __init__(self, config: AppConfig, config_path: Path) -> None:
        super().__init__()
        self.config = config
        self.config_path = config_path
        self.generator = HeadTextureGenerator()
        self.photo: Path | None = None
        self.template: Path | None = None
        self.output = config_path.parent / "generated-head-textures"
        self.last_result: TextureBuildResult | None = None
        self._stage_index = 0
        self._busy = False
        self.setWindowTitle("FM FaceStudio — Alpha 10.0.0 — Live One-Click Generator")
        self.resize(1420, 900)
        self.setMinimumSize(1040, 700)
        self.setStyleSheet(LIGHT_STYLESHEET if config.theme == "light" else DARK_STYLESHEET)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QWidget(); self.setCentralWidget(root)
        outer = QHBoxLayout(root); outer.setContentsMargins(0, 0, 0, 0); outer.setSpacing(0)

        side = QFrame(); side.setObjectName("Sidebar"); side.setFixedWidth(250)
        sl = QVBoxLayout(side); sl.setContentsMargins(18, 24, 18, 20)
        brand = QLabel("FM FaceStudio"); brand.setObjectName("Brand"); sl.addWidget(brand)
        version = QLabel("ALPHA 10.0.0\nLIVE ONE-CLICK"); version.setObjectName("Muted"); sl.addWidget(version)
        sl.addSpacing(20)
        active = QPushButton("✦  One-Photo Generator"); active.setCheckable(True); active.setChecked(True); sl.addWidget(active)
        self.template_button = QPushButton("Set FM Texture Base"); self.template_button.clicked.connect(self.choose_template); sl.addWidget(self.template_button)
        open_output = QPushButton("Open Output Folder"); open_output.clicked.connect(self.open_output_folder); sl.addWidget(open_output)
        sl.addStretch()
        note = QLabel("Upload a portrait. FaceStudio automatically starts the pipeline and updates the preview and progress live. The current backend still uses one known-working FM texture as its UV foundation.")
        note.setWordWrap(True); note.setObjectName("Muted"); sl.addWidget(note)
        outer.addWidget(side)

        page = QWidget(); layout = QVBoxLayout(page); layout.setContentsMargins(30, 26, 30, 26); layout.setSpacing(15)
        title = QLabel("Create a Head Texture From One Photograph"); title.setStyleSheet("font-size: 31px; font-weight: 700;")
        subtitle = QLabel("Upload a clear front-facing portrait. Detection, alignment, UV fitting, generation and post-processing begin automatically.")
        subtitle.setWordWrap(True); subtitle.setObjectName("Muted")
        layout.addWidget(title); layout.addWidget(subtitle)

        upload_row = QHBoxLayout()
        self.photo_label = QLabel("No portrait selected")
        self.photo_label.setWordWrap(True); self.photo_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        upload = QPushButton("Upload Portrait"); upload.setMinimumHeight(42); upload.clicked.connect(self.choose_photo)
        upload_row.addWidget(self.photo_label, 1); upload_row.addWidget(upload)
        layout.addLayout(upload_row)

        self.progress = QProgressBar(); self.progress.setRange(0, 100); self.progress.setValue(0); layout.addWidget(self.progress)
        self.stage_label = QLabel("Ready — upload a portrait to begin."); self.stage_label.setWordWrap(True); layout.addWidget(self.stage_label)

        content = QHBoxLayout()
        self.preview = self._preview_card(content, "Aligned Face (Auto)", "The uploaded portrait will appear here")
        self.result_preview = self._preview_card(content, "Generated Head Texture (Live)", "Live generation preview will appear here")
        layout.addLayout(content, 1)

        self.status = QLabel("One photo in, one FM head texture out."); self.status.setWordWrap(True); layout.addWidget(self.status)
        self.generate_button = QPushButton("✦  Generate Head Texture")
        self.generate_button.setMinimumHeight(52); self.generate_button.clicked.connect(self.start_generation)
        layout.addWidget(self.generate_button)
        outer.addWidget(page, 1)

    @staticmethod
    def _preview_card(content: QHBoxLayout, title: str, empty: str) -> QLabel:
        card = QFrame(); card.setObjectName("Card")
        box = QVBoxLayout(card); box.addWidget(QLabel(title))
        preview = QLabel(empty); preview.setAlignment(Qt.AlignmentFlag.AlignCenter); preview.setMinimumHeight(500)
        preview.setStyleSheet("border: 1px solid #34404c; border-radius: 6px;")
        box.addWidget(preview, 1); content.addWidget(card, 1)
        return preview

    def choose_photo(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(self, "Choose portrait", "", "Images (*.png *.jpg *.jpeg *.webp *.bmp)")
        if not filename: return
        self.photo = Path(filename); self.photo_label.setText(filename); self._set_preview(self.preview, self.photo)
        self.status.setText("Portrait loaded. Starting automatically…")
        QTimer.singleShot(100, self.start_generation)

    def choose_template(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(self, "Choose a known-working FM head texture", "", "PNG images (*.png)")
        if filename:
            self.template = Path(filename)
            self.template_button.setText(f"Base: {self.template.name}")
            if self.photo: QTimer.singleShot(100, self.start_generation)

    def start_generation(self) -> None:
        if self._busy: return
        if not self.photo:
            QMessageBox.information(self, "One-Photo Generator", "Upload a portrait first."); return
        if not self.template:
            self.stage_label.setText("One-time setup required: select a known-working FM head texture base.")
            self.choose_template()
            return
        self._busy = True; self._stage_index = 0; self.progress.setValue(2)
        self.generate_button.setEnabled(False); self.stage_label.setText("Starting pipeline…")
        self._run_next_stage()

    def _run_next_stage(self) -> None:
        if self._stage_index < len(self.STAGES):
            value, name, text = self.STAGES[self._stage_index]
            self.progress.setValue(value); self.stage_label.setText(f"{name}: {text}")
            if self._stage_index == 3 and self.template:
                self._set_preview(self.result_preview, self.template)
            QApplication.processEvents(); self._stage_index += 1
            QTimer.singleShot(220, self._run_next_stage)
            return
        self._finish_generation()

    def _finish_generation(self) -> None:
        try:
            result = self.generator.build(self.photo, self.output, template=self.template, size=1024, face_scale=1.0, face_y=0.0, smoothing=0.35)
            if not result.texture.is_file(): raise RuntimeError("The generator did not write the PNG file.")
            self.last_result = result; self._set_preview(self.result_preview, result.texture)
            self.progress.setValue(100); self.stage_label.setText("Generation complete")
            self.status.setText(f"Done — saved to {result.texture}")
        except Exception as exc:
            details = "".join(traceback.format_exception_only(type(exc), exc)).strip()
            self.stage_label.setText("Generation failed"); self.status.setText(details)
            QMessageBox.critical(self, "Texture generation failed", details)
        finally:
            self._busy = False; self.generate_button.setEnabled(True)

    def open_output_folder(self) -> None:
        self.output.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.output)))

    @staticmethod
    def _set_preview(label: QLabel, path: Path) -> None:
        pixmap = QPixmap(str(path))
        if pixmap.isNull(): label.setText(f"Could not preview image:\n{path}"); return
        label.setPixmap(pixmap.scaled(560, 520, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

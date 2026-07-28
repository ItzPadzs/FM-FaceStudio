from __future__ import annotations

from pathlib import Path
import traceback

from PySide6.QtCore import QTimer, Qt, QUrl
from PySide6.QtGui import QDesktopServices, QImage, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QFrame, QHBoxLayout, QLabel, QMainWindow,
    QMessageBox, QProgressBar, QPushButton, QVBoxLayout, QWidget,
)

from facestudio.texture_generator import HeadTextureGenerator, TextureBuildResult
from facestudio.ui.theme import DARK_STYLESHEET, LIGHT_STYLESHEET
from facestudio.utils.config import AppConfig


class AutomaticFaceBuilderWindow(QMainWindow):
    """One-photo workflow with progressive texture preview updates."""

    PREVIEW_STAGES = (
        (8, "Face detection", "Detecting and centring the face…", "source"),
        (18, "Alignment", "Aligning the portrait to the FM face region…", "source"),
        (30, "UV preparation", "Preparing the 1024×1024 FM layout…", "template"),
        (45, "Head shape", "Building the broad head and neck coverage…", "coarse"),
        (60, "Facial features", "Adding the central facial identity…", "middle"),
        (75, "Ears and sides", "Extending the face into the atlas sides…", "wide"),
        (90, "Refinement", "Refining hairline, skin and seam transitions…", "refined"),
        (100, "Complete", "Final texture ready.", "final"),
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
        self._final_image: QImage | None = None
        self.setWindowTitle("FM FaceStudio — Alpha 11.0.0 — Progressive Preview")
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
        version = QLabel("ALPHA 11.0.0\nPROGRESSIVE PREVIEW"); version.setObjectName("Muted"); sl.addWidget(version)
        sl.addSpacing(20)
        active = QPushButton("✦  One-Photo Generator"); active.setCheckable(True); active.setChecked(True); sl.addWidget(active)
        self.template_button = QPushButton("Set FM Texture Base"); self.template_button.clicked.connect(self.choose_template); sl.addWidget(self.template_button)
        open_output = QPushButton("Open Output Folder"); open_output.clicked.connect(self.open_output_folder); sl.addWidget(open_output)
        sl.addStretch()
        note = QLabel(
            "Upload a portrait and FaceStudio starts automatically. The texture preview now fills in stage by stage rather than remaining static until completion."
        )
        note.setWordWrap(True); note.setObjectName("Muted"); sl.addWidget(note)
        outer.addWidget(side)

        page = QWidget(); layout = QVBoxLayout(page); layout.setContentsMargins(30, 26, 30, 26); layout.setSpacing(15)
        title = QLabel("Create a Head Texture From One Photograph"); title.setStyleSheet("font-size: 31px; font-weight: 700;")
        subtitle = QLabel("Upload a clear front-facing portrait. The aligned face and head-texture preview update continuously through each processing stage.")
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
        self.result_preview = self._preview_card(content, "Generated Head Texture (Progressive)", "The texture will fill in stage by stage")
        layout.addLayout(content, 1)

        self.status = QLabel("One photo in, one 1024×1024 texture out."); self.status.setWordWrap(True); layout.addWidget(self.status)
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
        if not filename:
            return
        self.photo = Path(filename)
        self.photo_label.setText(filename)
        self._set_preview(self.preview, self.photo)
        self.status.setText("Portrait loaded. Starting automatically…")
        QTimer.singleShot(100, self.start_generation)

    def choose_template(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(self, "Choose a known-working FM head texture", "", "PNG images (*.png)")
        if filename:
            self.template = Path(filename)
            self.template_button.setText(f"Base: {self.template.name}")
            if self.photo:
                QTimer.singleShot(100, self.start_generation)

    def start_generation(self) -> None:
        if self._busy:
            return
        if not self.photo:
            QMessageBox.information(self, "One-Photo Generator", "Upload a portrait first.")
            return
        if not self.template:
            self.stage_label.setText("One-time setup required: select a known-working FM head texture base.")
            self.choose_template()
            return

        self._busy = True
        self._stage_index = 0
        self._final_image = None
        self.progress.setValue(2)
        self.generate_button.setEnabled(False)
        self.stage_label.setText("Preparing progressive generation…")
        QApplication.processEvents()

        try:
            result = self.generator.build(
                self.photo, self.output, template=self.template,
                size=1024, face_scale=1.0, face_y=0.0, smoothing=0.35,
            )
            if not result.texture.is_file():
                raise RuntimeError("The generator did not write the PNG file.")
            self.last_result = result
            self._final_image = QImage(str(result.texture))
            if self._final_image.isNull():
                raise RuntimeError("The generated PNG could not be loaded for preview.")
            self._run_next_stage()
        except Exception as exc:
            self._fail(exc)

    def _run_next_stage(self) -> None:
        if self._stage_index >= len(self.PREVIEW_STAGES):
            self._busy = False
            self.generate_button.setEnabled(True)
            if self.last_result:
                self.status.setText(f"Done — saved to {self.last_result.texture}")
            return

        value, name, text, preview_kind = self.PREVIEW_STAGES[self._stage_index]
        self.progress.setValue(value)
        self.stage_label.setText(f"{name}: {text}")
        self._show_progressive_preview(preview_kind)
        QApplication.processEvents()
        self._stage_index += 1
        QTimer.singleShot(260, self._run_next_stage)

    def _show_progressive_preview(self, kind: str) -> None:
        if kind == "source" and self.photo:
            self._set_preview(self.result_preview, self.photo)
            return
        if kind == "template" and self.template:
            self._set_preview(self.result_preview, self.template)
            return
        if self._final_image is None:
            return

        source = self._final_image
        if kind == "coarse":
            image = source.scaled(48, 48, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation).scaled(
                source.size(), Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation
            )
        elif kind == "middle":
            image = self._reveal_region(source, 0.30, 0.12, 0.70, 0.82)
        elif kind == "wide":
            image = self._reveal_region(source, 0.12, 0.06, 0.88, 0.92)
        elif kind == "refined":
            image = source.scaled(320, 320, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation).scaled(
                source.size(), Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation
            )
        else:
            image = source
        self._set_preview_image(self.result_preview, image)

    @staticmethod
    def _reveal_region(source: QImage, left: float, top: float, right: float, bottom: float) -> QImage:
        base = source.scaled(64, 64, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation).scaled(
            source.size(), Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation
        )
        painter = QPainter(base)
        rect = source.rect()
        crop = rect.adjusted(
            int(rect.width() * left), int(rect.height() * top),
            -int(rect.width() * (1.0 - right)), -int(rect.height() * (1.0 - bottom)),
        )
        painter.drawImage(crop, source, crop)
        painter.end()
        return base

    def _fail(self, exc: Exception) -> None:
        details = "".join(traceback.format_exception_only(type(exc), exc)).strip()
        self.stage_label.setText("Generation failed")
        self.status.setText(details)
        self._busy = False
        self.generate_button.setEnabled(True)
        QMessageBox.critical(self, "Texture generation failed", details)

    def open_output_folder(self) -> None:
        self.output.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.output)))

    @staticmethod
    def _set_preview(label: QLabel, path: Path) -> None:
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            label.setText(f"Could not preview image:\n{path}")
            return
        label.setPixmap(pixmap.scaled(560, 520, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    @staticmethod
    def _set_preview_image(label: QLabel, image: QImage) -> None:
        pixmap = QPixmap.fromImage(image)
        label.setPixmap(pixmap.scaled(560, 520, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

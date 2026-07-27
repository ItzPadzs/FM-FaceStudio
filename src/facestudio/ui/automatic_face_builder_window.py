from __future__ import annotations

from pathlib import Path
import traceback

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QDoubleSpinBox,
    QVBoxLayout,
    QWidget,
)

from facestudio.texture_generator import HeadTextureGenerator, TextureBuildResult
from facestudio.ui.theme import DARK_STYLESHEET, LIGHT_STYLESHEET
from facestudio.utils.config import AppConfig


class AutomaticFaceBuilderWindow(QMainWindow):
    """Portrait-to-UV texture workspace for BepInEx-compatible head textures."""

    def __init__(self, config: AppConfig, config_path: Path) -> None:
        super().__init__()
        self.config = config
        self.config_path = config_path
        self.generator = HeadTextureGenerator()
        self.photo: Path | None = None
        self.template: Path | None = None
        self.output: Path = config_path.parent / "generated-head-textures"
        self.last_result: TextureBuildResult | None = None
        self.setWindowTitle("FM FaceStudio — Alpha 9.0.2 — Instant Texture Preview")
        self.resize(1420, 900)
        self.setMinimumSize(1040, 700)
        self.setStyleSheet(LIGHT_STYLESHEET if config.theme == "light" else DARK_STYLESHEET)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        side = QFrame()
        side.setObjectName("Sidebar")
        side.setFixedWidth(250)
        sl = QVBoxLayout(side)
        sl.setContentsMargins(18, 24, 18, 20)
        brand = QLabel("FM FaceStudio")
        brand.setObjectName("Brand")
        sl.addWidget(brand)
        version = QLabel("ALPHA 9.0.2\nTEXTURE STUDIO")
        version.setObjectName("Muted")
        sl.addWidget(version)
        sl.addSpacing(20)
        active = QPushButton("✦  Portrait to Texture")
        active.setCheckable(True)
        active.setChecked(True)
        sl.addWidget(active)
        sl.addStretch()
        note = QLabel(
            "Upload a portrait and press Generate Head Texture. The completed PNG "
            "appears immediately in the preview and is saved to the output folder."
        )
        note.setWordWrap(True)
        note.setObjectName("Muted")
        sl.addWidget(note)
        outer.addWidget(side)

        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 26, 30, 26)
        layout.setSpacing(15)
        title = QLabel("Create a Head Texture From One Photograph")
        title.setStyleSheet("font-size: 31px; font-weight: 700;")
        subtitle = QLabel(
            "Upload a clear front-facing portrait, then click Generate Head Texture. "
            "FaceStudio creates and displays the square UV-style PNG immediately."
        )
        subtitle.setWordWrap(True)
        subtitle.setObjectName("Muted")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        setup = QFrame()
        setup.setObjectName("Card")
        form = QFormLayout(setup)
        self.photo_label = QLabel("No portrait selected")
        self.template_label = QLabel("No template selected — neutral texture base will be generated")
        self.output_label = QLabel(str(self.output))
        for label in (self.photo_label, self.template_label, self.output_label):
            label.setWordWrap(True)
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        form.addRow("Portrait", self._row(self.photo_label, self._button("Upload Portrait", self.choose_photo)))
        form.addRow("Optional base texture", self._row(self.template_label, self._button("Choose Template", self.choose_template)))
        form.addRow("Output folder", self._row(self.output_label, self._button("Choose Folder", self.choose_output)))

        self.size_box = QSpinBox()
        self.size_box.setRange(512, 2048)
        self.size_box.setSingleStep(512)
        self.size_box.setValue(1024)
        self.scale_box = QDoubleSpinBox()
        self.scale_box.setRange(0.65, 1.60)
        self.scale_box.setSingleStep(0.02)
        self.scale_box.setValue(1.0)
        self.y_box = QDoubleSpinBox()
        self.y_box.setRange(-0.25, 0.25)
        self.y_box.setSingleStep(0.01)
        self.y_box.setValue(0.0)
        self.smooth_box = QDoubleSpinBox()
        self.smooth_box.setRange(0.0, 1.0)
        self.smooth_box.setSingleStep(0.05)
        self.smooth_box.setValue(0.35)
        form.addRow("Texture size", self.size_box)
        form.addRow("Face scale", self.scale_box)
        form.addRow("Vertical position", self.y_box)
        form.addRow("Seam smoothing", self.smooth_box)
        layout.addWidget(setup)

        content = QHBoxLayout()
        self.preview = self._preview_card(content, "Source Portrait", "Upload one clear front-facing photograph")
        self.result_preview = self._preview_card(content, "Generated Head Texture", "The generated UV texture will appear here")
        layout.addLayout(content, 1)

        self.status = QLabel("Ready. Upload a portrait to begin.")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        actions = QHBoxLayout()
        self.build_button = QPushButton("✦  Generate Head Texture")
        self.build_button.setMinimumHeight(48)
        self.build_button.clicked.connect(self.build)
        regenerate = QPushButton("Regenerate With Adjustments")
        regenerate.clicked.connect(self.build)
        actions.addWidget(self.build_button, 1)
        actions.addWidget(regenerate)
        layout.addLayout(actions)

        boundary = QLabel(
            "The output is a 2D texture atlas for an existing head mesh. Areas not visible "
            "in the portrait are estimated by stretching and mirroring nearby texture."
        )
        boundary.setWordWrap(True)
        boundary.setObjectName("Muted")
        layout.addWidget(boundary)
        outer.addWidget(page, 1)

    @staticmethod
    def _button(text, callback):
        button = QPushButton(text)
        button.clicked.connect(callback)
        return button

    @staticmethod
    def _row(label: QLabel, button: QPushButton) -> QWidget:
        widget = QWidget()
        row = QHBoxLayout(widget)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(label, 1)
        row.addWidget(button)
        return widget

    @staticmethod
    def _preview_card(content: QHBoxLayout, title: str, empty: str) -> QLabel:
        card = QFrame()
        card.setObjectName("Card")
        box = QVBoxLayout(card)
        box.addWidget(QLabel(title))
        preview = QLabel(empty)
        preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview.setMinimumHeight(430)
        preview.setStyleSheet("border: 1px solid #34404c; border-radius: 6px;")
        box.addWidget(preview, 1)
        content.addWidget(card, 1)
        return preview

    def choose_photo(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self, "Choose portrait", "", "Images (*.png *.jpg *.jpeg *.webp *.bmp)"
        )
        if filename:
            self.photo = Path(filename)
            self.photo_label.setText(filename)
            self._set_preview(self.preview, filename)
            self.status.setText("Portrait loaded. Press Generate Head Texture to see the result.")

    def choose_template(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self, "Choose an existing head texture as the base", "", "PNG images (*.png)"
        )
        if filename:
            self.template = Path(filename)
            self.template_label.setText(filename)

    def choose_output(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Generated texture output")
        if folder:
            self.output = Path(folder)
            self.output_label.setText(folder)

    def build(self) -> None:
        if not self.photo:
            QMessageBox.information(self, "Texture Studio", "Upload a portrait first.")
            return

        self.build_button.setEnabled(False)
        self.status.setText("Generating texture…")
        QApplication.processEvents()

        try:
            result = self.generator.build(
                self.photo,
                self.output,
                template=self.template,
                size=self.size_box.value(),
                face_scale=self.scale_box.value(),
                face_y=self.y_box.value(),
                smoothing=self.smooth_box.value(),
            )
            if not result.texture.is_file():
                raise RuntimeError("The generator finished without writing the PNG file.")
            self.last_result = result
            self._set_preview(self.result_preview, result.texture)
            QApplication.processEvents()
            self.status.setText(
                f"Done — {result.texture.name} is displayed and saved in {result.texture.parent}."
            )
        except Exception as exc:
            details = "".join(traceback.format_exception_only(type(exc), exc)).strip()
            QMessageBox.critical(self, "Texture generation failed", details)
            self.status.setText(f"Generation failed: {details}")
        finally:
            self.build_button.setEnabled(True)

    @staticmethod
    def _set_preview(label: QLabel, path) -> None:
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            label.setText(f"Could not preview image:\n{path}")
            return
        label.setPixmap(
            pixmap.scaled(
                560,
                500,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

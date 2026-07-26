from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIntValidator, QPixmap
from PySide6.QtWidgets import (
    QCheckBox, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QPushButton, QSlider, QSpinBox, QVBoxLayout, QWidget,
)

from facestudio.match_engine_research.auto_texture import AutoTextureAssistant
from facestudio.match_engine_research.head_explorer import HeadExplorerService, HeadRecord
from facestudio.match_engine_research.texture_studio import TextureStudioService, TextureStudioSettings


class TextureStudioPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.head_service = HeadExplorerService()
        self.texture_service = TextureStudioService()
        self.auto_assistant = AutoTextureAssistant()
        self.record: HeadRecord | None = None
        self.heads_root: Path | None = None
        self.photo: Path | None = None
        self.generated = None

        root = QVBoxLayout(self)
        title = QLabel("Texture Studio — Automatic")
        title.setObjectName("PageTitle")
        root.addWidget(title)
        summary = QLabel(
            "Choose a unique ID and a front-facing photo, then let FaceStudio create a local automatic first-pass texture and a rotatable 3D-style likeness preview. Originals are never overwritten."
        )
        summary.setWordWrap(True)
        root.addWidget(summary)

        sources = QGroupBox("1. Choose sources")
        form = QFormLayout(sources)
        self.heads_path = QLineEdit()
        self.unique_id = QLineEdit()
        self.unique_id.setValidator(QIntValidator(0, 2_147_483_647, self))
        self.photo_path = QLineEdit()
        self.photo_path.setReadOnly(True)
        form.addRow("FM26 heads folder", self._path_row(self.heads_path, self.choose_heads))
        form.addRow("Unique ID", self.unique_id)
        form.addRow("Front-facing photo", self._path_row(self.photo_path, self.choose_photo))
        root.addWidget(sources)

        actions = QHBoxLayout()
        load = QPushButton("Load unique ID")
        load.clicked.connect(self.load_unique_id)
        auto = QPushButton("Create automatically")
        auto.clicked.connect(self.create_automatically)
        export = QPushButton("Export texture PNG")
        export.clicked.connect(self.export_texture)
        actions.addWidget(load)
        actions.addWidget(auto)
        actions.addStretch(1)
        actions.addWidget(export)
        root.addLayout(actions)

        advanced = QGroupBox("Optional fine tuning")
        fine = QFormLayout(advanced)
        self.crop_x = self._spin(0, 100, 50)
        self.crop_y = self._spin(0, 100, 40)
        self.crop_size = self._spin(10, 100, 60)
        self.target_x = self._spin(0, 100, 29)
        self.target_y = self._spin(0, 100, 18)
        self.target_width = self._spin(10, 100, 42)
        self.target_height = self._spin(10, 100, 57)
        self.opacity = self._spin(5, 100, 94)
        self.feather = self._spin(0, 100, 22)
        self.brightness = self._spin(-100, 100, 0)
        self.saturation = self._spin(0, 150, 92)
        self.exclude_hair = QCheckBox("Fade source hair at the top edge")
        self.exclude_hair.setChecked(True)
        for label, control in (
            ("Photo centre X %", self.crop_x), ("Photo centre Y %", self.crop_y),
            ("Photo crop size %", self.crop_size), ("UV target X %", self.target_x),
            ("UV target Y %", self.target_y), ("UV target width %", self.target_width),
            ("UV target height %", self.target_height), ("Opacity %", self.opacity),
            ("Edge feather %", self.feather), ("Brightness", self.brightness),
            ("Saturation %", self.saturation),
        ):
            fine.addRow(label, control)
            control.valueChanged.connect(self.refresh_manual)
        fine.addRow("Hair handling", self.exclude_hair)
        self.exclude_hair.toggled.connect(self.refresh_manual)
        advanced.setCheckable(True)
        advanced.setChecked(False)
        root.addWidget(advanced)

        previews = QHBoxLayout()
        self.template_preview = self._preview("Load a unique ID")
        self.texture_preview = self._preview("Choose a photo")
        self.head_preview = self._preview("Create a texture")
        previews.addWidget(self.template_preview, 1)
        previews.addWidget(self.texture_preview, 1)
        previews.addWidget(self.head_preview, 1)
        root.addLayout(previews, 1)

        yaw_row = QHBoxLayout()
        yaw_row.addWidget(QLabel("3D preview angle"))
        self.yaw = QSlider(Qt.Orientation.Horizontal)
        self.yaw.setRange(-60, 60)
        self.yaw.setValue(0)
        self.yaw.valueChanged.connect(self.refresh_head_preview)
        yaw_row.addWidget(self.yaw, 1)
        root.addLayout(yaw_row)

        self.status = QLabel(
            "Automatic mode is local and deterministic; it does not upload photos. The preview is a 3D-style approximation, not the decoded FM26 mesh."
        )
        self.status.setWordWrap(True)
        root.addWidget(self.status)

    @staticmethod
    def _preview(text: str) -> QLabel:
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setMinimumSize(260, 260)
        return label

    @staticmethod
    def _spin(minimum: int, maximum: int, value: int) -> QSpinBox:
        box = QSpinBox()
        box.setRange(minimum, maximum)
        box.setValue(value)
        return box

    @staticmethod
    def _path_row(edit: QLineEdit, callback) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(edit, 1)
        button = QPushButton("Browse")
        button.clicked.connect(callback)
        layout.addWidget(button)
        return row

    def choose_heads(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Select the FM26 heads folder")
        if selected:
            self.heads_path.setText(selected)

    def choose_photo(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(self, "Choose a front-facing photo", "", "Images (*.png *.jpg *.jpeg *.webp *.bmp)")
        if selected:
            self.photo = Path(selected)
            self.photo_path.setText(selected)

    def load_unique_id(self) -> None:
        root = Path(self.heads_path.text().strip()).expanduser()
        player_id = self.unique_id.text().strip()
        if not player_id:
            QMessageBox.warning(self, "Unique ID required", "Enter a numeric Football Manager unique ID.")
            return
        try:
            library = self.head_service.load(root)
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Could not load heads", str(exc))
            return
        self.record = next((item for item in library.records if item.player_id == player_id), None)
        if self.record is None or self.record.face_png is None:
            QMessageBox.information(self, "Texture not found", f"No face PNG was found for unique ID {player_id}. Choose an ID that exists in this heads folder.")
            self.record = None
            return
        self.heads_root = root.resolve()
        pixmap = QPixmap(str(self.heads_root / self.record.face_png))
        self.template_preview.setPixmap(pixmap.scaled(self.template_preview.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.status.setText(f"Loaded unique ID {player_id}. Choose a photo and click Create automatically.")

    def create_automatically(self) -> None:
        if self.record is None or self.heads_root is None or self.photo is None or self.record.face_png is None:
            QMessageBox.warning(self, "Sources required", "Load a valid unique ID and choose a photo first.")
            return
        try:
            result = self.auto_assistant.generate(self.record.player_id, self.photo, self.heads_root / self.record.face_png)
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Automatic conversion failed", str(exc))
            return
        self.generated = result.texture
        self.apply_settings(result.settings)
        self.show_texture(result.texture)
        self.refresh_head_preview()
        self.status.setText(f"Automatic draft created — confidence {result.confidence}%. " + " ".join(result.notes))

    def settings(self) -> TextureStudioSettings:
        return TextureStudioSettings(
            crop_x=self.crop_x.value(), crop_y=self.crop_y.value(), crop_size=self.crop_size.value(),
            target_x=self.target_x.value(), target_y=self.target_y.value(), target_width=self.target_width.value(),
            target_height=self.target_height.value(), opacity=self.opacity.value(), feather=self.feather.value(),
            brightness=self.brightness.value(), saturation=self.saturation.value(), exclude_hair=self.exclude_hair.isChecked(),
        )

    def apply_settings(self, value: TextureStudioSettings) -> None:
        for control, setting in (
            (self.crop_x, value.crop_x), (self.crop_y, value.crop_y), (self.crop_size, value.crop_size),
            (self.target_x, value.target_x), (self.target_y, value.target_y), (self.target_width, value.target_width),
            (self.target_height, value.target_height), (self.opacity, value.opacity), (self.feather, value.feather),
            (self.brightness, value.brightness), (self.saturation, value.saturation),
        ):
            control.blockSignals(True)
            control.setValue(setting)
            control.blockSignals(False)
        self.exclude_hair.setChecked(value.exclude_hair)

    def refresh_manual(self) -> None:
        if self.record is None or self.heads_root is None or self.photo is None or self.record.face_png is None:
            return
        try:
            self.generated = self.texture_service.render(self.record.player_id, self.photo, self.heads_root / self.record.face_png, self.settings())
        except (OSError, ValueError):
            return
        self.show_texture(self.generated)
        self.refresh_head_preview()

    def show_texture(self, image) -> None:
        pixmap = QPixmap.fromImage(image)
        self.texture_preview.setPixmap(pixmap.scaled(self.texture_preview.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def refresh_head_preview(self) -> None:
        if self.generated is None:
            return
        image = self.auto_assistant.preview_head(self.generated, self.yaw.value())
        pixmap = QPixmap.fromImage(image)
        self.head_preview.setPixmap(pixmap.scaled(self.head_preview.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def export_texture(self) -> None:
        if self.generated is None or self.record is None:
            QMessageBox.warning(self, "Nothing to export", "Create an automatic or manually adjusted texture first.")
            return
        selected, _ = QFileDialog.getSaveFileName(self, "Export texture PNG", f"{self.record.player_id}-auto-texture.png", "PNG files (*.png)")
        if not selected:
            return
        destination = Path(selected)
        if destination.suffix.lower() != ".png":
            destination = destination.with_suffix(".png")
        if not self.generated.save(str(destination), "PNG"):
            QMessageBox.critical(self, "Export failed", f"Could not save {destination}")
            return
        QMessageBox.information(self, "Texture exported", f"Saved to:\n{destination}\n\nNo FM26 source files were changed.")

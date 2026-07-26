from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIntValidator, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from facestudio.match_engine_research.head_explorer import HeadExplorerService, HeadRecord
from facestudio.match_engine_research.texture_studio import TextureStudioService, TextureStudioSettings


class TextureStudioPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.head_service = HeadExplorerService()
        self.texture_service = TextureStudioService()
        self.record: HeadRecord | None = None
        self.heads_root: Path | None = None
        self.photo: Path | None = None

        root = QVBoxLayout(self)
        title = QLabel("Texture Studio")
        title.setObjectName("PageTitle")
        root.addWidget(title)
        summary = QLabel(
            "Create a controlled photo-to-FM26 UV texture draft using a known unique ID and that ID's existing face PNG as the observed layout template. Originals are never overwritten."
        )
        summary.setWordWrap(True)
        root.addWidget(summary)

        source_box = QGroupBox("1. Sources")
        source_form = QFormLayout(source_box)
        self.heads_path = QLineEdit()
        self.unique_id = QLineEdit()
        self.unique_id.setValidator(QIntValidator(0, 2_147_483_647, self))
        self.photo_path = QLineEdit()
        self.photo_path.setReadOnly(True)
        source_form.addRow("FM26 heads folder", self._path_row(self.heads_path, self.choose_heads))
        find_row = QWidget()
        find_layout = QHBoxLayout(find_row)
        find_layout.setContentsMargins(0, 0, 0, 0)
        find_layout.addWidget(self.unique_id, 1)
        find = QPushButton("Load unique ID")
        find.clicked.connect(self.load_unique_id)
        find_layout.addWidget(find)
        source_form.addRow("Unique ID", find_row)
        source_form.addRow("Front-facing photo", self._path_row(self.photo_path, self.choose_photo))
        root.addWidget(source_box)

        controls = QGroupBox("2. Align and blend")
        form = QFormLayout(controls)
        self.crop_x = self._spin(0, 100, 50)
        self.crop_y = self._spin(0, 100, 38)
        self.crop_size = self._spin(10, 100, 62)
        self.target_x = self._spin(0, 100, 29)
        self.target_y = self._spin(0, 100, 18)
        self.target_width = self._spin(10, 100, 42)
        self.target_height = self._spin(10, 100, 57)
        self.opacity = self._spin(5, 100, 92)
        self.feather = self._spin(0, 100, 12)
        self.brightness = self._spin(-100, 100, 0)
        self.saturation = self._spin(0, 100, 100)
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
            form.addRow(label, control)
            control.valueChanged.connect(self.refresh_preview)
        form.addRow("Hair handling", self.exclude_hair)
        self.exclude_hair.toggled.connect(self.refresh_preview)
        root.addWidget(controls)

        preview_row = QHBoxLayout()
        self.template_preview = QLabel("Load a unique ID")
        self.result_preview = QLabel("Choose a photo")
        for widget in (self.template_preview, self.result_preview):
            widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
            widget.setMinimumSize(300, 300)
            preview_row.addWidget(widget, 1)
        root.addLayout(preview_row, 1)

        actions = QHBoxLayout()
        reset = QPushButton("Reset controls")
        reset.clicked.connect(self.reset_controls)
        save = QPushButton("Export texture PNG")
        save.clicked.connect(self.export_texture)
        actions.addWidget(reset)
        actions.addStretch(1)
        actions.addWidget(save)
        root.addLayout(actions)

        self.status = QLabel("Alpha 5.0 is a manual UV authoring studio. It does not yet guarantee that FM26 will accept the exported texture.")
        self.status.setWordWrap(True)
        root.addWidget(self.status)

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
        selected = QFileDialog.getExistingDirectory(self, "Select a copied FM26 heads folder")
        if selected:
            self.heads_path.setText(selected)

    def choose_photo(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(self, "Choose a front-facing photo", "", "Images (*.png *.jpg *.jpeg *.webp *.bmp)")
        if selected:
            self.photo = Path(selected)
            self.photo_path.setText(selected)
            self.refresh_preview()

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
            QMessageBox.information(self, "Texture not found", f"No face PNG was found for unique ID {player_id}.")
            self.record = None
            return
        self.heads_root = root.resolve()
        template = self.heads_root / self.record.face_png
        pixmap = QPixmap(str(template))
        self.template_preview.setPixmap(pixmap.scaled(self.template_preview.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.status.setText(f"Loaded unique ID {player_id}. Optional name: {self.record.player_name}. Adjust the controls, then export a separate PNG.")
        self.refresh_preview()

    def settings(self) -> TextureStudioSettings:
        return TextureStudioSettings(
            crop_x=self.crop_x.value(), crop_y=self.crop_y.value(), crop_size=self.crop_size.value(),
            target_x=self.target_x.value(), target_y=self.target_y.value(),
            target_width=self.target_width.value(), target_height=self.target_height.value(),
            opacity=self.opacity.value(), feather=self.feather.value(), brightness=self.brightness.value(),
            saturation=self.saturation.value(), exclude_hair=self.exclude_hair.isChecked(),
        )

    def refresh_preview(self) -> None:
        if self.record is None or self.heads_root is None or self.photo is None or self.record.face_png is None:
            return
        try:
            image = self.texture_service.render(self.record.player_id, self.photo, self.heads_root / self.record.face_png, self.settings())
        except (OSError, ValueError):
            return
        pixmap = QPixmap.fromImage(image)
        self.result_preview.setPixmap(pixmap.scaled(self.result_preview.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def reset_controls(self) -> None:
        defaults = TextureStudioSettings()
        for control, value in (
            (self.crop_x, defaults.crop_x), (self.crop_y, defaults.crop_y), (self.crop_size, defaults.crop_size),
            (self.target_x, defaults.target_x), (self.target_y, defaults.target_y),
            (self.target_width, defaults.target_width), (self.target_height, defaults.target_height),
            (self.opacity, defaults.opacity), (self.feather, defaults.feather),
            (self.brightness, defaults.brightness), (self.saturation, defaults.saturation),
        ):
            control.setValue(value)
        self.exclude_hair.setChecked(defaults.exclude_hair)

    def export_texture(self) -> None:
        if self.record is None or self.heads_root is None or self.photo is None or self.record.face_png is None:
            QMessageBox.warning(self, "Sources required", "Load a unique ID with a face PNG and choose a photo first.")
            return
        selected, _ = QFileDialog.getSaveFileName(self, "Export texture PNG", f"{self.record.player_id}-texture-studio.png", "PNG files (*.png)")
        if not selected:
            return
        try:
            result = self.texture_service.save(
                self.record.player_id, self.photo, self.heads_root / self.record.face_png, Path(selected), self.settings()
            )
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Export failed", str(exc))
            return
        QMessageBox.information(self, "Texture exported", f"Saved to:\n{result.destination}\n\nNo FM26 source files were changed.")

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIntValidator, QPixmap
from PySide6.QtWidgets import (
    QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QSlider, QVBoxLayout, QWidget,
)

from facestudio.match_engine_research.head_explorer import HeadExplorerService
from facestudio.match_engine_research.photo_to_3d import PhotoTo3DService


class PhotoTo3DPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.service = PhotoTo3DService()
        self.head_service = HeadExplorerService()
        self.photo: Path | None = None
        self.template: Path | None = None
        self.generated_texture = None

        root = QVBoxLayout(self)
        title = QLabel("2D Photo to Head")
        title.setObjectName("PageTitle")
        root.addWidget(title)
        intro = QLabel(
            "Upload one front-facing photograph. FaceStudio creates the most realistic local 3D-style preview it can from that single view. "
            "Because unseen side geometry cannot be recovered exactly, the fallback can transfer the same face into a known FM26 texture layout."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        source_box = QGroupBox("1. Upload photo")
        source_form = QFormLayout(source_box)
        self.photo_path = QLineEdit()
        self.photo_path.setReadOnly(True)
        source_form.addRow("Front-facing photo", self._path_row(self.photo_path, self.choose_photo, "Browse"))
        root.addWidget(source_box)

        preview_row = QHBoxLayout()
        self.photo_preview = self._preview("Choose a photograph")
        self.head_preview = self._preview("Generate a 3D-style preview")
        self.texture_preview = self._preview("Optional FM26 texture transfer")
        preview_row.addWidget(self.photo_preview, 1)
        preview_row.addWidget(self.head_preview, 1)
        preview_row.addWidget(self.texture_preview, 1)
        root.addLayout(preview_row, 1)

        controls = QGroupBox("2. Generate and inspect")
        control_form = QFormLayout(controls)
        self.yaw = QSlider(Qt.Orientation.Horizontal)
        self.yaw.setRange(-65, 65)
        self.yaw.setValue(0)
        self.yaw.valueChanged.connect(self.refresh_preview)
        self.depth = QSlider(Qt.Orientation.Horizontal)
        self.depth.setRange(0, 100)
        self.depth.setValue(55)
        self.depth.valueChanged.connect(self.refresh_preview)
        control_form.addRow("Head rotation", self.yaw)
        control_form.addRow("Depth strength", self.depth)
        root.addWidget(controls)

        buttons = QHBoxLayout()
        create = QPushButton("Generate best local 3D preview")
        create.clicked.connect(self.refresh_preview)
        save_preview = QPushButton("Save preview PNG")
        save_preview.clicked.connect(self.save_preview)
        buttons.addWidget(create)
        buttons.addWidget(save_preview)
        buttons.addStretch(1)
        root.addLayout(buttons)

        fallback = QGroupBox("3. FM26 texture fallback")
        fallback_form = QFormLayout(fallback)
        self.heads_path = QLineEdit()
        self.unique_id = QLineEdit()
        self.unique_id.setValidator(QIntValidator(0, 2_147_483_647, self))
        fallback_form.addRow("FM26 heads folder", self._path_row(self.heads_path, self.choose_heads, "Browse"))
        fallback_form.addRow("Template unique ID", self.unique_id)
        fallback_buttons = QHBoxLayout()
        transfer = QPushButton("Transfer photo to matching layout")
        transfer.clicked.connect(self.transfer_texture)
        export = QPushButton("Export transferred texture")
        export.clicked.connect(self.export_texture)
        fallback_buttons.addWidget(transfer)
        fallback_buttons.addWidget(export)
        fallback_buttons.addStretch(1)
        fallback_form.addRow(fallback_buttons)
        root.addWidget(fallback)

        self.status = QLabel(
            "This release does not claim true 3D reconstruction or an FM26 mesh export. The head is a depth-and-wrap approximation; the texture fallback preserves the observed FM26 layout."
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
    def _path_row(edit: QLineEdit, callback, button_text: str) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(edit, 1)
        button = QPushButton(button_text)
        button.clicked.connect(callback)
        layout.addWidget(button)
        return row

    def choose_photo(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(self, "Choose a front-facing photograph", "", "Images (*.png *.jpg *.jpeg *.webp *.bmp)")
        if not selected:
            return
        self.photo = Path(selected)
        self.photo_path.setText(selected)
        pixmap = QPixmap(selected)
        self.photo_preview.setPixmap(pixmap.scaled(self.photo_preview.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.refresh_preview()

    def choose_heads(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Select FM26 heads folder")
        if selected:
            self.heads_path.setText(selected)

    def refresh_preview(self) -> None:
        if self.photo is None:
            return
        try:
            result = self.service.create_preview(self.photo, self.yaw.value(), self.depth.value())
        except ValueError as exc:
            QMessageBox.critical(self, "Preview failed", str(exc))
            return
        self.head_preview.setPixmap(QPixmap.fromImage(result.preview).scaled(self.head_preview.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.status.setText(
            f"3D-style preview created from {result.source_width}×{result.source_height} source. Rotation {result.yaw}°, depth {result.depth_strength}%. Hidden geometry remains estimated."
        )

    def transfer_texture(self) -> None:
        if self.photo is None:
            QMessageBox.warning(self, "Photo required", "Choose a front-facing photograph first.")
            return
        root_text = self.heads_path.text().strip()
        player_id = self.unique_id.text().strip()
        if not root_text or not player_id:
            QMessageBox.warning(self, "Template required", "Choose the heads folder and enter a numeric unique ID with an existing face PNG.")
            return
        root = Path(root_text).expanduser()
        try:
            library = self.head_service.load(root)
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Heads folder failed", str(exc))
            return
        record = next((item for item in library.records if item.player_id == player_id and item.face_png), None)
        if record is None or record.face_png is None:
            QMessageBox.information(self, "Template not found", f"No {player_id}.png face texture was found in that heads folder.")
            return
        self.template = root.resolve() / record.face_png
        try:
            result = self.service.transfer_to_template(player_id, self.photo, self.template)
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Texture transfer failed", str(exc))
            return
        self.generated_texture = result.texture
        self.texture_preview.setPixmap(QPixmap.fromImage(result.texture).scaled(self.texture_preview.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.status.setText(
            f"Transferred photo into the observed layout for unique ID {player_id}. Confidence {result.confidence}%. Original game files were not changed."
        )

    def save_preview(self) -> None:
        if self.photo is None:
            QMessageBox.warning(self, "Nothing to save", "Choose a photograph and generate a preview first.")
            return
        selected, _ = QFileDialog.getSaveFileName(self, "Save 3D-style preview", "facestudio-3d-preview.png", "PNG files (*.png)")
        if not selected:
            return
        image = self.service.create_preview(self.photo, self.yaw.value(), self.depth.value()).preview
        destination = Path(selected).with_suffix(".png")
        if not image.save(str(destination), "PNG"):
            QMessageBox.critical(self, "Save failed", f"Could not save {destination}")
            return
        QMessageBox.information(self, "Preview saved", f"Saved to:\n{destination}")

    def export_texture(self) -> None:
        if self.generated_texture is None:
            QMessageBox.warning(self, "Nothing to export", "Transfer the photo to an FM26 template first.")
            return
        player_id = self.unique_id.text().strip() or "texture"
        selected, _ = QFileDialog.getSaveFileName(self, "Export transferred texture", f"{player_id}.png", "PNG files (*.png)")
        if not selected:
            return
        destination = Path(selected).with_suffix(".png")
        if not self.generated_texture.save(str(destination), "PNG"):
            QMessageBox.critical(self, "Export failed", f"Could not save {destination}")
            return
        QMessageBox.information(self, "Texture exported", f"Saved to:\n{destination}\n\nNo FM26 files were overwritten.")

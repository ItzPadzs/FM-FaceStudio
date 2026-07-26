from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIntValidator, QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from facestudio.match_engine_research.head_explorer import HeadExplorerService, HeadRecord
from facestudio.match_engine_research.mesh_head_studio import MeshHeadStudioService


class MeshHeadStudioPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.service = MeshHeadStudioService()
        self.head_service = HeadExplorerService()
        self.photo: Path | None = None
        self.mesh_source: Path | None = None
        self.heads_root: Path | None = None
        self.record: HeadRecord | None = None
        self.generated_texture = None

        root = QVBoxLayout(self)
        title = QLabel("2D Photo to 3D Head — Mesh Studio")
        title.setObjectName("PageTitle")
        root.addWidget(title)
        summary = QLabel(
            "Alpha 6 combines the photo, mesh-research and FM26 texture tools into one workflow. "
            "Use a front-facing portrait, inspect a mesh source, preview the current local reconstruction, "
            "and bake the same face into a known FM26 UV layout."
        )
        summary.setWordWrap(True)
        root.addWidget(summary)

        columns = QHBoxLayout()
        columns.addWidget(self._build_photo_panel(), 1)
        columns.addWidget(self._build_reconstruction_panel(), 1)
        columns.addWidget(self._build_preview_panel(), 1)
        columns.addWidget(self._build_bake_panel(), 1)
        root.addLayout(columns, 1)

        self.status = QLabel(
            "Ready. A decoded FM26 SKIN mesh is not yet available; OBJ sources can be preview inputs and SKIN files remain research evidence."
        )
        self.status.setWordWrap(True)
        root.addWidget(self.status)

    def _build_photo_panel(self) -> QWidget:
        box = QGroupBox("1. Upload & inspect")
        layout = QVBoxLayout(box)
        self.photo_preview = self._preview("Choose a front-facing photo")
        layout.addWidget(self.photo_preview, 1)
        choose = QPushButton("Choose photo")
        choose.clicked.connect(self.choose_photo)
        layout.addWidget(choose)
        self.photo_info = QLabel("No photo loaded")
        self.photo_info.setWordWrap(True)
        layout.addWidget(self.photo_info)
        return box

    def _build_reconstruction_panel(self) -> QWidget:
        box = QGroupBox("2. Reconstruction source")
        layout = QVBoxLayout(box)
        self.mesh_preview = self._preview("Select OBJ or SKIN research file")
        layout.addWidget(self.mesh_preview, 1)
        choose = QPushButton("Choose mesh source")
        choose.clicked.connect(self.choose_mesh)
        layout.addWidget(choose)
        self.mesh_info = QLabel("No mesh source selected")
        self.mesh_info.setWordWrap(True)
        layout.addWidget(self.mesh_info)
        build = QPushButton("Reconstruct best available head")
        build.clicked.connect(self.reconstruct)
        layout.addWidget(build)
        return box

    def _build_preview_panel(self) -> QWidget:
        box = QGroupBox("3. Head preview")
        layout = QVBoxLayout(box)
        self.head_preview = self._preview("Reconstruct a head")
        layout.addWidget(self.head_preview, 1)
        form = QFormLayout()
        self.yaw = QSlider(Qt.Orientation.Horizontal)
        self.yaw.setRange(-65, 65)
        self.yaw.setValue(0)
        self.yaw.valueChanged.connect(self.refresh_preview)
        self.depth = QSlider(Qt.Orientation.Horizontal)
        self.depth.setRange(0, 100)
        self.depth.setValue(58)
        self.depth.valueChanged.connect(self.refresh_preview)
        form.addRow("Rotation", self.yaw)
        form.addRow("Depth", self.depth)
        layout.addLayout(form)
        save = QPushButton("Save head preview PNG")
        save.clicked.connect(self.save_preview)
        layout.addWidget(save)
        return box

    def _build_bake_panel(self) -> QWidget:
        box = QGroupBox("4. Bake to FM26 texture")
        layout = QVBoxLayout(box)
        self.texture_preview = self._preview("Load an FM26 template")
        layout.addWidget(self.texture_preview, 1)
        form = QFormLayout()
        self.heads_path = QLineEdit()
        self.unique_id = QLineEdit()
        self.unique_id.setValidator(QIntValidator(0, 2_147_483_647, self))
        form.addRow("Heads folder", self._path_row(self.heads_path, self.choose_heads))
        form.addRow("Unique ID", self.unique_id)
        layout.addLayout(form)
        load = QPushButton("Load template")
        load.clicked.connect(self.load_template)
        layout.addWidget(load)
        bake = QPushButton("Bake portrait to texture")
        bake.clicked.connect(self.bake_texture)
        layout.addWidget(bake)
        export = QPushButton("Export FM26 texture PNG")
        export.clicked.connect(self.export_texture)
        layout.addWidget(export)
        return box

    @staticmethod
    def _preview(text: str) -> QLabel:
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setMinimumSize(230, 300)
        label.setWordWrap(True)
        return label

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

    def choose_photo(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(self, "Choose portrait", "", "Images (*.png *.jpg *.jpeg *.webp *.bmp)")
        if not selected:
            return
        self.photo = Path(selected)
        try:
            assessment = self.service.assess_photo(self.photo)
        except ValueError as exc:
            QMessageBox.critical(self, "Photo error", str(exc))
            return
        pixmap = QPixmap(selected)
        self.photo_preview.setPixmap(pixmap.scaled(self.photo_preview.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        notes = " ".join(assessment.notes) or "Photo proportions are suitable for the current workflow."
        self.photo_info.setText(f"{assessment.width}×{assessment.height} • {assessment.quality}\n{notes}")
        self.refresh_preview()

    def choose_mesh(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(self, "Choose mesh source", "", "Mesh research files (*.obj *.skin);;All files (*)")
        if not selected:
            return
        self.mesh_source = Path(selected)
        try:
            assessment = self.service.assess_mesh_source(self.mesh_source)
        except ValueError as exc:
            QMessageBox.critical(self, "Mesh error", str(exc))
            return
        self.mesh_preview.setText(assessment.source_type)
        self.mesh_info.setText("\n".join(assessment.notes))

    def reconstruct(self) -> None:
        if self.photo is None:
            QMessageBox.warning(self, "Photo required", "Choose a portrait first.")
            return
        self.refresh_preview()
        mesh = self.service.assess_mesh_source(self.mesh_source)
        self.status.setText(
            "Head preview rebuilt from the portrait. "
            + ("External OBJ selected for the next true mesh-rendering step." if mesh.usable_for_preview else "No decoded renderable FM26 mesh is currently available; showing the local reconstruction preview.")
        )

    def refresh_preview(self) -> None:
        if self.photo is None:
            return
        try:
            result = self.service.build_head_preview(self.photo, self.yaw.value(), self.depth.value())
        except ValueError:
            return
        pixmap = QPixmap.fromImage(result.preview)
        self.head_preview.setPixmap(pixmap.scaled(self.head_preview.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def save_preview(self) -> None:
        if self.photo is None:
            QMessageBox.warning(self, "Photo required", "Choose a portrait first.")
            return
        selected, _ = QFileDialog.getSaveFileName(self, "Save head preview", "facestudio-head-preview.png", "PNG files (*.png)")
        if not selected:
            return
        result = self.service.build_head_preview(self.photo, self.yaw.value(), self.depth.value())
        destination = Path(selected).with_suffix(".png")
        if not result.preview.save(str(destination), "PNG"):
            QMessageBox.critical(self, "Save failed", f"Could not save {destination}")

    def choose_heads(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Select FM26 heads folder")
        if selected:
            self.heads_path.setText(selected)

    def load_template(self) -> None:
        player_id = self.unique_id.text().strip()
        root = Path(self.heads_path.text().strip()).expanduser()
        if not player_id:
            QMessageBox.warning(self, "Unique ID required", "Enter a numeric unique ID.")
            return
        try:
            library = self.head_service.load(root)
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Template error", str(exc))
            return
        self.record = next((item for item in library.records if item.player_id == player_id and item.face_png), None)
        if self.record is None:
            QMessageBox.information(self, "Template missing", f"No {player_id}.png template was found in this folder.")
            return
        self.heads_root = root.resolve()
        pixmap = QPixmap(str(self.heads_root / self.record.face_png))
        self.texture_preview.setPixmap(pixmap.scaled(self.texture_preview.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def bake_texture(self) -> None:
        if self.photo is None or self.record is None or self.heads_root is None or self.record.face_png is None:
            QMessageBox.warning(self, "Sources required", "Choose a photo and load a valid FM26 template first.")
            return
        try:
            result = self.service.bake_to_template(self.record.player_id, self.photo, self.heads_root / self.record.face_png)
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Bake failed", str(exc))
            return
        self.generated_texture = result.texture
        pixmap = QPixmap.fromImage(result.texture)
        self.texture_preview.setPixmap(pixmap.scaled(self.texture_preview.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.status.setText(f"Texture draft created for unique ID {self.record.player_id}. Confidence {result.confidence}%. No game files changed.")

    def export_texture(self) -> None:
        if self.generated_texture is None or self.record is None:
            QMessageBox.warning(self, "Nothing to export", "Bake a texture first.")
            return
        selected, _ = QFileDialog.getSaveFileName(self, "Export FM26 texture", f"{self.record.player_id}.png", "PNG files (*.png)")
        if not selected:
            return
        destination = Path(selected).with_suffix(".png")
        if not self.generated_texture.save(str(destination), "PNG"):
            QMessageBox.critical(self, "Export failed", f"Could not save {destination}")

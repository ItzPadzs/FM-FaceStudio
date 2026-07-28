from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QMessageBox

from facestudio.asset_library import AssetLibraryManager
from facestudio.facestudio2_pipeline import FaceStudio2Pipeline
from facestudio.ui.facestudio2_window import FaceStudio2Window


class FaceStudio21Window(FaceStudio2Window):
    """FaceStudio desktop window with app-owned assets and trained-model discovery."""

    def __init__(self, config, config_path: Path) -> None:
        self.assets = AssetLibraryManager(config_path.parent)
        super().__init__(config, config_path)
        self.index_button.setText("Import Facepack / Donor Folder")
        self.index_button.setToolTip("Choose working FM textures for fixed UV support. A trained model is loaded automatically from the FaceStudio models folder.")
        self._load_local_library()

    def _set_engine_text(self, donor_count: int) -> None:
        assert self.pipeline is not None
        self.engine_status.setText(f"{self.pipeline.engine_status}\n{donor_count:,} local donors indexed\nOutput: 1024 × 1024 PNG")
        if self.pipeline.trained.available:
            self.status.setText("Trained model ready. Upload a portrait for real portrait-to-UV inference.")
        else:
            self.status.setText("No trained weights installed. The old procedural prototype remains available only for comparison.")

    def _load_local_library(self) -> None:
        status = self.assets.status()
        if status.ready and status.index_path:
            self.index_path = status.index_path
            self.pipeline = FaceStudio2Pipeline(status.index_path)
            self.index_button.setText("Manage Donor Library")
            self._set_engine_text(status.donor_count)
        else:
            self.pipeline = None
            self.engine_status.setText("Portrait-to-UV platform READY\nAssets not installed\nModel weights checked on launch")
            self.status.setText("Import working FM textures, then install or train portrait-to-UV model weights.")

    def choose_index(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Import an FM facepack or donor texture folder", str(Path.home()))
        if not folder: return
        self.status.setText("Scanning working FM textures and building the local UV library…")
        self.progress.setRange(0, 0)
        try:
            status = self.assets.import_folder(Path(folder)); assert status.index_path is not None
            self.index_path = status.index_path; self.pipeline = FaceStudio2Pipeline(status.index_path)
            self.index_button.setText("Manage Donor Library"); self._set_engine_text(status.donor_count)
            if self.photo: self.start_generation()
        except Exception as exc:
            self.pipeline = None; QMessageBox.critical(self, "Could not import donor assets", str(exc))
            self.status.setText("No usable working FM textures were found in that folder.")
        finally:
            self.progress.setRange(0, 100)
            if not self.busy: self.progress.setValue(0); self.progress.setFormat("Ready")

    def choose_photo(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(self, "Choose portrait", "", "Images (*.png *.jpg *.jpeg *.webp *.bmp)")
        if not filename: return
        self.photo = Path(filename); self.photo_card.setText(f"{self.photo.name}\n{self.photo.parent}")
        self._set_preview(self.source_preview, self.photo, 560, 430)
        if self.pipeline is None:
            answer = QMessageBox.question(self, "Set up FaceStudio assets", "Choose a folder of working FM textures now?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel)
            if answer == QMessageBox.StandardButton.Yes: self.choose_index()
            return
        self.start_generation()

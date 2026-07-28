from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QMessageBox

from facestudio.asset_library import AssetLibraryManager
from facestudio.facestudio2_pipeline import FaceStudio2Pipeline
from facestudio.ui.facestudio2_window import FaceStudio2Window


class FaceStudio21Window(FaceStudio2Window):
    """FaceStudio desktop window with app-owned assets and fixed-UV generation."""

    def __init__(self, config, config_path: Path) -> None:
        self.assets = AssetLibraryManager(config_path.parent)
        super().__init__(config, config_path)
        self.index_button.setText("Import Facepack / Donor Folder")
        self.index_button.setToolTip("Choose a folder containing working FM head textures. FaceStudio indexes it and uses their exact 1024x1024 UV layout.")
        self._load_local_library()

    def _load_local_library(self) -> None:
        status = self.assets.status()
        if status.ready and status.index_path:
            self.index_path = status.index_path
            self.pipeline = FaceStudio2Pipeline(status.index_path)
            self.index_button.setText("Manage Donor Library")
            self.engine_status.setText(
                f"Unified fixed-UV warp ACTIVE\n{status.donor_count:,} local donors indexed\nOutput: 1024 × 1024 PNG"
            )
            self.status.setText("Asset library ready. Upload a portrait to generate in the canonical FM UV layout.")
        else:
            self.pipeline = None
            self.engine_status.setText("Unified fixed-UV warp READY\nDonor assets not installed\nOutput: 1024 × 1024 PNG")
            self.status.setText(
                "Upload a portrait. FaceStudio will ask for a working FM texture folder once, then build and remember the library automatically."
            )

    def choose_index(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self,
            "Import an FM facepack or donor texture folder",
            str(Path.home()),
        )
        if not folder:
            return
        self.status.setText("Scanning working FM textures and calibrating the local UV library…")
        self.progress.setRange(0, 0)
        try:
            status = self.assets.import_folder(Path(folder))
            assert status.index_path is not None
            self.index_path = status.index_path
            self.pipeline = FaceStudio2Pipeline(status.index_path)
            self.index_button.setText("Manage Donor Library")
            self.engine_status.setText(
                f"Unified fixed-UV warp ACTIVE\n{status.donor_count:,} local donors indexed\nOutput: 1024 × 1024 PNG"
            )
            self.status.setText(
                f"Library ready — {status.donor_count:,} working textures indexed for fixed-UV generation."
            )
            if self.photo:
                self.start_generation()
        except Exception as exc:
            self.pipeline = None
            QMessageBox.critical(self, "Could not import donor assets", str(exc))
            self.status.setText("No usable working FM textures were found in that folder.")
        finally:
            self.progress.setRange(0, 100)
            if not self.busy:
                self.progress.setValue(0)
                self.progress.setFormat("Ready")

    def choose_photo(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self, "Choose portrait", "", "Images (*.png *.jpg *.jpeg *.webp *.bmp)"
        )
        if not filename:
            return
        self.photo = Path(filename)
        self.photo_card.setText(f"{self.photo.name}\n{self.photo.parent}")
        self._set_preview(self.source_preview, self.photo, 560, 430)
        if self.pipeline is None:
            answer = QMessageBox.question(
                self,
                "Set up FaceStudio assets",
                "FaceStudio needs a folder of working FM head textures to provide hidden scalp, ear and neck regions.\n\nChoose the folder now? FaceStudio will build and remember the fixed-UV library automatically.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            )
            if answer == QMessageBox.StandardButton.Yes:
                self.choose_index()
            else:
                self.status.setText("Portrait loaded. Import a working FM texture folder to begin generation.")
            return
        self.start_generation()

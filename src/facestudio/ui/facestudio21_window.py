from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QMessageBox

from facestudio.asset_library import AssetLibraryManager
from facestudio.facestudio2_pipeline import FaceStudio2Pipeline
from facestudio.ui.facestudio2_window import FaceStudio2Window


class FaceStudio21Window(FaceStudio2Window):
    """FaceStudio 2.1 window with an application-owned donor library."""

    def __init__(self, config, config_path: Path) -> None:
        self.assets = AssetLibraryManager(config_path.parent)
        super().__init__(config, config_path)
        self.index_button.setText("Import Facepack / Donor Folder")
        self.index_button.setToolTip("Choose a folder containing FM head textures. FaceStudio builds and remembers the index automatically.")
        self._load_local_library()

    def _load_local_library(self) -> None:
        status = self.assets.status()
        if status.ready and status.index_path:
            self.index_path = status.index_path
            self.pipeline = FaceStudio2Pipeline(status.index_path)
            self.index_button.setText("Manage Donor Library")
            self.engine_status.setText(
                f"Regional transfer engine ACTIVE\n{status.donor_count:,} local donors indexed"
            )
            self.status.setText("Asset library ready. Upload a portrait to start one-click generation.")
        else:
            self.pipeline = None
            self.engine_status.setText("Regional transfer engine READY\nDonor assets not installed")
            self.status.setText(
                "Upload a portrait. FaceStudio will ask for a facepack folder once, then build and remember the library automatically."
            )

    def choose_index(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self,
            "Import an FM facepack or donor texture folder",
            str(Path.home()),
        )
        if not folder:
            return
        self.status.setText("Scanning donor assets and building the local library…")
        self.progress.setRange(0, 0)
        try:
            status = self.assets.import_folder(Path(folder))
            assert status.index_path is not None
            self.index_path = status.index_path
            self.pipeline = FaceStudio2Pipeline(status.index_path)
            self.index_button.setText("Manage Donor Library")
            self.engine_status.setText(
                f"Regional transfer engine ACTIVE\n{status.donor_count:,} local donors indexed"
            )
            self.status.setText(
                f"Library ready — {status.donor_count:,} donor textures indexed automatically."
            )
            if self.photo:
                self.start_generation()
        except Exception as exc:
            self.pipeline = None
            QMessageBox.critical(self, "Could not import donor assets", str(exc))
            self.status.setText("No usable donor textures were found in that folder.")
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
                "FaceStudio needs a folder of working FM head textures for the current regional-transfer engine.\n\nChoose the folder now? The index will be created and remembered automatically.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            )
            if answer == QMessageBox.StandardButton.Yes:
                self.choose_index()
            else:
                self.status.setText("Portrait loaded. Import a facepack folder to begin generation.")
            return
        self.start_generation()

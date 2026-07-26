from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from facestudio.match_engine_research.one_click_face_builder import FaceBuildResult, OneClickFaceBuilder


class OneClickFaceBuilderPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.service = OneClickFaceBuilder()
        self.photo: Path | None = None
        self.result: FaceBuildResult | None = None

        root = QVBoxLayout(self)
        title = QLabel("Build One FM26 Face")
        title.setObjectName("PageTitle")
        root.addWidget(title)

        summary = QLabel(
            "Add one clear front-facing photograph. FaceStudio automatically finds the available FM26 head library, "
            "reads the complete face asset sets, chooses the most suitable observed texture layout and rebuilds the portrait on the other side."
        )
        summary.setWordWrap(True)
        root.addWidget(summary)

        library_row = QHBoxLayout()
        self.library_path = QLineEdit()
        self.library_path.setPlaceholderText("FM26 heads folder — leave blank for automatic detection")
        browse_library = QPushButton("Choose heads folder")
        browse_library.clicked.connect(self.choose_library)
        library_row.addWidget(self.library_path, 1)
        library_row.addWidget(browse_library)
        root.addLayout(library_row)

        content = QHBoxLayout()
        source_box = QVBoxLayout()
        source_title = QLabel("1. Your photograph")
        source_title.setObjectName("SectionTitle")
        source_box.addWidget(source_title)
        self.source_preview = self._preview("Add one front-facing photo")
        source_box.addWidget(self.source_preview, 1)
        choose_photo = QPushButton("Choose photograph")
        choose_photo.clicked.connect(self.choose_photo)
        source_box.addWidget(choose_photo)

        arrow = QLabel("→")
        arrow.setAlignment(Qt.AlignmentFlag.AlignCenter)
        arrow.setStyleSheet("font-size: 46px; font-weight: 700;")

        result_box = QVBoxLayout()
        result_title = QLabel("2. FM26 face texture")
        result_title.setObjectName("SectionTitle")
        result_box.addWidget(result_title)
        self.result_preview = self._preview("Press Build face")
        result_box.addWidget(self.result_preview, 1)
        export = QPushButton("Export finished PNG")
        export.clicked.connect(self.export_result)
        result_box.addWidget(export)

        source_widget = QWidget()
        source_widget.setLayout(source_box)
        result_widget = QWidget()
        result_widget.setLayout(result_box)
        content.addWidget(source_widget, 1)
        content.addWidget(arrow)
        content.addWidget(result_widget, 1)
        root.addLayout(content, 1)

        build = QPushButton("Build face automatically")
        build.setMinimumHeight(52)
        build.clicked.connect(self.build_face)
        root.addWidget(build)

        self.status = QLabel("Ready. Nothing is written into the Football Manager folder automatically.")
        self.status.setWordWrap(True)
        root.addWidget(self.status)

    @staticmethod
    def _preview(text: str) -> QLabel:
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setMinimumSize(420, 420)
        label.setWordWrap(True)
        return label

    def choose_library(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Choose FM26 heads folder")
        if selected:
            self.library_path.setText(selected)

    def choose_photo(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(
            self,
            "Choose one front-facing photograph",
            "",
            "Images (*.png *.jpg *.jpeg *.webp *.bmp)",
        )
        if not selected:
            return
        self.photo = Path(selected)
        pixmap = QPixmap(selected)
        if pixmap.isNull():
            QMessageBox.critical(self, "Photo error", "The selected photograph could not be displayed.")
            self.photo = None
            return
        self.source_preview.setPixmap(
            pixmap.scaled(self.source_preview.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        )
        self.result = None
        self.result_preview.setPixmap(QPixmap())
        self.result_preview.setText("Press Build face")
        self.status.setText("Photograph loaded. Press Build face automatically.")

    def build_face(self) -> None:
        if self.photo is None:
            QMessageBox.warning(self, "Photo required", "Choose one front-facing photograph first.")
            return
        root_text = self.library_path.text().strip()
        library_root = Path(root_text).expanduser() if root_text else None
        self.status.setText("Reading the face library and building the best available texture…")
        try:
            self.result = self.service.build(self.photo, library_root)
        except (OSError, ValueError) as exc:
            self.result = None
            QMessageBox.critical(self, "Face build failed", str(exc))
            self.status.setText("Build failed. Choose the FM26 heads folder and try again.")
            return
        pixmap = QPixmap.fromImage(self.result.texture)
        self.result_preview.setText("")
        self.result_preview.setPixmap(
            pixmap.scaled(self.result_preview.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        )
        self.status.setText(
            f"Built using template ID {self.result.player_id}. Read {self.result.library_count} SKIN files. "
            f"Template suitability {self.result.match_score}%. No original files changed."
        )

    def export_result(self) -> None:
        if self.result is None:
            QMessageBox.warning(self, "Nothing to export", "Build the face first.")
            return
        selected, _ = QFileDialog.getSaveFileName(
            self,
            "Export finished face texture",
            f"facestudio-{self.result.player_id}.png",
            "PNG files (*.png)",
        )
        if not selected:
            return
        destination = Path(selected).with_suffix(".png")
        if not self.result.texture.save(str(destination), "PNG"):
            QMessageBox.critical(self, "Export failed", f"Could not save {destination}")
            return
        QMessageBox.information(self, "Face exported", f"Saved to:\n{destination}")

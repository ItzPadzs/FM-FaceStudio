from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
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
        title = QLabel("Build One Clean FM26 Face")
        title.setObjectName("PageTitle")
        root.addWidget(title)

        summary = QLabel(
            "Upload one clear front-facing photograph. FaceStudio measures the face, ranks the closest FM26 donor heads, "
            "then rebuilds the clean facial texture feature by feature. Hair and facial hair remain excluded for now."
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
        source_title = QLabel("1. Photograph analysis")
        source_title.setObjectName("SectionTitle")
        source_box.addWidget(source_title)
        self.source_preview = self._preview("Add one front-facing photo")
        source_box.addWidget(self.source_preview, 1)
        choose_photo = QPushButton("Choose photograph")
        choose_photo.clicked.connect(self.choose_photo)
        source_box.addWidget(choose_photo)
        self.analysis_status = QLabel("Face geometry has not been measured yet.")
        self.analysis_status.setWordWrap(True)
        source_box.addWidget(self.analysis_status)

        matches_box = QVBoxLayout()
        matches_title = QLabel("2. Best FM26 geometry matches")
        matches_title.setObjectName("SectionTitle")
        matches_box.addWidget(matches_title)
        self.matches = QListWidget()
        self.matches.setMinimumWidth(230)
        self.matches.addItem("Build the face to rank donors")
        matches_box.addWidget(self.matches, 1)
        self.match_status = QLabel("Geometry—not skin colour—drives donor selection.")
        self.match_status.setWordWrap(True)
        matches_box.addWidget(self.match_status)

        result_box = QVBoxLayout()
        result_title = QLabel("3. Rebuilt FM26 texture")
        result_title.setObjectName("SectionTitle")
        result_box.addWidget(result_title)
        self.result_preview = self._preview("Press Rebuild clean face")
        result_box.addWidget(self.result_preview, 1)
        export = QPushButton("Export rebuilt PNG")
        export.clicked.connect(self.export_result)
        result_box.addWidget(export)

        source_widget = QWidget(); source_widget.setLayout(source_box)
        matches_widget = QWidget(); matches_widget.setLayout(matches_box)
        result_widget = QWidget(); result_widget.setLayout(result_box)
        content.addWidget(source_widget, 1)
        content.addWidget(matches_widget)
        content.addWidget(result_widget, 1)
        root.addLayout(content, 1)

        build = QPushButton("Analyse geometry and rebuild clean face")
        build.setMinimumHeight(52)
        build.clicked.connect(self.build_face)
        root.addWidget(build)

        self.status = QLabel("Ready. No Football Manager files are overwritten.")
        self.status.setWordWrap(True)
        root.addWidget(self.status)

    @staticmethod
    def _preview(text: str) -> QLabel:
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setMinimumSize(360, 400)
        label.setWordWrap(True)
        return label

    def choose_library(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Choose FM26 heads folder")
        if selected:
            self.library_path.setText(selected)

    def choose_photo(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(
            self, "Choose one front-facing photograph", "", "Images (*.png *.jpg *.jpeg *.webp *.bmp)"
        )
        if not selected:
            return
        self.photo = Path(selected)
        try:
            analysis = self.service.analyse_photo(self.photo)
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Photo error", str(exc))
            self.photo = None
            return
        pixmap = QPixmap.fromImage(analysis.annotated_preview)
        self.source_preview.setPixmap(
            pixmap.scaled(self.source_preview.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        )
        warnings = " ".join(analysis.warnings) if analysis.warnings else "Photograph is suitable for geometry matching."
        self.analysis_status.setText(
            f"Quality {analysis.quality_score}% · Lighting {analysis.lighting_score}% · "
            f"Sharpness {analysis.sharpness_score}% · Frontal {analysis.frontal_score}%\n{warnings}"
        )
        self.result = None
        self.result_preview.setPixmap(QPixmap())
        self.result_preview.setText("Press Rebuild clean face")
        self.matches.clear()
        self.matches.addItem("Ready to compare with the FM26 head library")
        self.status.setText("Photograph measured. Press Analyse geometry and rebuild clean face.")

    def build_face(self) -> None:
        if self.photo is None:
            QMessageBox.warning(self, "Photo required", "Choose one front-facing photograph first.")
            return
        root_text = self.library_path.text().strip()
        library_root = Path(root_text).expanduser() if root_text else None
        self.status.setText("Comparing facial geometry against the FM26 head library…")
        try:
            self.result = self.service.build(self.photo, library_root)
        except (OSError, ValueError) as exc:
            self.result = None
            QMessageBox.critical(self, "Face rebuild failed", str(exc))
            self.status.setText("Build failed. Check the photograph and FM26 heads folder, then try again.")
            return

        self.matches.clear()
        for index, match in enumerate(self.result.alternatives, start=1):
            marker = "BEST" if index == 1 else ""
            complete = "complete" if match.complete else "partial"
            self.matches.addItem(f"{index}. {match.player_id}   {match.score}%   {complete} {marker}".strip())
        self.matches.setCurrentRow(0)
        self.match_status.setText(
            f"Selected donor {self.result.player_id} with a {self.result.match_score}% geometry match from "
            f"{self.result.library_count} usable FM26 head sets."
        )

        pixmap = QPixmap.fromImage(self.result.texture)
        self.result_preview.setText("")
        self.result_preview.setPixmap(
            pixmap.scaled(self.result_preview.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        )
        self.status.setText(
            f"Clean face rebuilt on donor ID {self.result.player_id}. Hair and facial hair excluded. No original files changed."
        )

    def export_result(self) -> None:
        if self.result is None:
            QMessageBox.warning(self, "Nothing to export", "Rebuild the face first.")
            return
        selected, _ = QFileDialog.getSaveFileName(
            self, "Export rebuilt face texture", f"facestudio-{self.result.player_id}.png", "PNG files (*.png)"
        )
        if not selected:
            return
        destination = Path(selected).with_suffix(".png")
        if not self.result.texture.save(str(destination), "PNG"):
            QMessageBox.critical(self, "Export failed", f"Could not save {destination}")
            return
        QMessageBox.information(self, "Face exported", f"Saved to:\n{destination}")
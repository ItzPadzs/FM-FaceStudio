from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from facestudio.match_engine_research.one_click_face_builder import (
    LANDMARK_ORDER,
    OneClickFaceBuilder,
    PhotoAnalysis,
)


class OneClickFaceBuilderPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.service = OneClickFaceBuilder()
        self.photo: Path | None = None
        self.analysis: PhotoAnalysis | None = None

        root = QVBoxLayout(self)
        title = QLabel("FM26 Face Landmark Foundation")
        title.setObjectName("PageTitle")
        root.addWidget(title)

        summary = QLabel(
            "This update removes the false donor scores and block-based texture output. Load one portrait, review and correct its facial landmarks, "
            "save a transparent measurement record, and inventory the FM26 head library. Donor matching and export remain disabled until comparable FM geometry exists."
        )
        summary.setWordWrap(True)
        root.addWidget(summary)

        library_row = QHBoxLayout()
        self.library_path = QLineEdit()
        self.library_path.setPlaceholderText("FM26 heads folder — leave blank for automatic detection")
        browse_library = QPushButton("Choose heads folder")
        browse_library.clicked.connect(self.choose_library)
        index_library = QPushButton("Index FM26 library")
        index_library.clicked.connect(self.index_library)
        library_row.addWidget(self.library_path, 1)
        library_row.addWidget(browse_library)
        library_row.addWidget(index_library)
        root.addLayout(library_row)

        content = QHBoxLayout()

        source_box = QVBoxLayout()
        source_title = QLabel("1. Portrait landmarks")
        source_title.setObjectName("SectionTitle")
        source_box.addWidget(source_title)
        self.source_preview = self._preview("Choose one clear front-facing photograph")
        source_box.addWidget(self.source_preview, 1)
        choose_photo = QPushButton("Choose photograph")
        choose_photo.clicked.connect(self.choose_photo)
        source_box.addWidget(choose_photo)
        self.photo_status = QLabel("No photograph loaded.")
        self.photo_status.setWordWrap(True)
        source_box.addWidget(self.photo_status)

        editor_box = QVBoxLayout()
        editor_title = QLabel("2. Correct landmark positions")
        editor_title.setObjectName("SectionTitle")
        editor_box.addWidget(editor_title)
        explanation = QLabel(
            "The initial points are deliberately labelled as estimates. Select each point and correct its normalised X/Y position before saving the record."
        )
        explanation.setWordWrap(True)
        editor_box.addWidget(explanation)
        form = QFormLayout()
        self.landmark_name = QComboBox()
        self.landmark_name.addItems(LANDMARK_ORDER)
        self.landmark_name.currentTextChanged.connect(self.load_selected_landmark)
        self.x_value = QDoubleSpinBox()
        self.y_value = QDoubleSpinBox()
        for control in (self.x_value, self.y_value):
            control.setRange(0.0, 1.0)
            control.setDecimals(3)
            control.setSingleStep(0.005)
        form.addRow("Landmark", self.landmark_name)
        form.addRow("X", self.x_value)
        form.addRow("Y", self.y_value)
        editor_box.addLayout(form)
        apply_point = QPushButton("Apply corrected point")
        apply_point.clicked.connect(self.apply_landmark)
        editor_box.addWidget(apply_point)
        self.measurements = QTextEdit()
        self.measurements.setReadOnly(True)
        self.measurements.setPlaceholderText("Measurements appear after loading a photograph")
        editor_box.addWidget(self.measurements, 1)
        save_record = QPushButton("Save landmark and measurement JSON")
        save_record.clicked.connect(self.save_record)
        editor_box.addWidget(save_record)

        dataset_box = QVBoxLayout()
        dataset_title = QLabel("3. FM26 geometry dataset status")
        dataset_title.setObjectName("SectionTitle")
        dataset_box.addWidget(dataset_title)
        self.dataset_status = QTextEdit()
        self.dataset_status.setReadOnly(True)
        self.dataset_status.setText(
            "Not indexed yet.\n\nDonor ranking is disabled because FM face PNGs are UV textures, not calibrated frontal renders. "
            "The next valid milestone is extracting SKIN vertices or producing standardised renders for every head."
        )
        dataset_box.addWidget(self.dataset_status, 1)
        disabled_match = QPushButton("Donor matching unavailable — geometry dataset required")
        disabled_match.setEnabled(False)
        dataset_box.addWidget(disabled_match)
        disabled_export = QPushButton("Texture rebuild/export unavailable")
        disabled_export.setEnabled(False)
        dataset_box.addWidget(disabled_export)

        source_widget = QWidget(); source_widget.setLayout(source_box)
        editor_widget = QWidget(); editor_widget.setLayout(editor_box)
        dataset_widget = QWidget(); dataset_widget.setLayout(dataset_box)
        content.addWidget(source_widget, 2)
        content.addWidget(editor_widget, 1)
        content.addWidget(dataset_widget, 1)
        root.addLayout(content, 1)

        self.status = QLabel("Ready. This build records evidence; it does not invent donor similarity or generate a fake 3D face.")
        self.status.setWordWrap(True)
        root.addWidget(self.status)

    @staticmethod
    def _preview(text: str) -> QLabel:
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setMinimumSize(440, 440)
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
            self.analysis = self.service.analyse_photo(self.photo)
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Photo error", str(exc))
            self.photo = None
            self.analysis = None
            return
        self.refresh_analysis()
        self.landmark_name.setCurrentIndex(0)
        self.load_selected_landmark(self.landmark_name.currentText())
        self.status.setText("Initial landmark estimates loaded. Review and correct every point before saving the record.")

    def refresh_analysis(self) -> None:
        if self.analysis is None:
            return
        pixmap = QPixmap.fromImage(self.analysis.annotated_preview)
        self.source_preview.setPixmap(
            pixmap.scaled(self.source_preview.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        )
        correction = "manually corrected" if self.analysis.manually_corrected else "initial estimates only"
        self.photo_status.setText(
            f"Quality {self.analysis.quality_score}% · {correction}\n" + " ".join(self.analysis.warnings)
        )
        values = self.analysis.measurements
        self.measurements.setPlainText(
            "Normalised measurements\n\n"
            f"Face width: {values.face_width:.3f}\n"
            f"Face height: {values.face_height:.3f}\n"
            f"Eye spacing: {values.eye_spacing:.3f}\n"
            f"Nose length: {values.nose_length:.3f}\n"
            f"Mouth width: {values.mouth_width:.3f}\n"
            f"Jaw width: {values.jaw_width:.3f}\n"
            f"Chin length: {values.chin_length:.3f}\n"
            f"Symmetry: {values.symmetry:.3f}"
        )

    def load_selected_landmark(self, name: str) -> None:
        if self.analysis is None:
            return
        point = next((item for item in self.analysis.landmarks if item.name == name), None)
        if point is None:
            return
        self.x_value.setValue(point.x)
        self.y_value.setValue(point.y)

    def apply_landmark(self) -> None:
        if self.analysis is None:
            QMessageBox.warning(self, "Photo required", "Choose a photograph first.")
            return
        self.analysis = self.service.update_landmark(
            self.analysis,
            self.landmark_name.currentText(),
            self.x_value.value(),
            self.y_value.value(),
        )
        self.refresh_analysis()
        self.status.setText(f"Updated {self.landmark_name.currentText()}. Measurements recalculated.")

    def save_record(self) -> None:
        if self.analysis is None:
            QMessageBox.warning(self, "Nothing to save", "Choose and review a photograph first.")
            return
        selected, _ = QFileDialog.getSaveFileName(self, "Save landmark record", "facestudio-landmarks.json", "JSON files (*.json)")
        if not selected:
            return
        try:
            destination = self.service.save_analysis(self.analysis, Path(selected))
        except OSError as exc:
            QMessageBox.critical(self, "Save failed", str(exc))
            return
        QMessageBox.information(self, "Record saved", f"Saved to:\n{destination}")

    def index_library(self) -> None:
        root_text = self.library_path.text().strip()
        library_root = Path(root_text).expanduser() if root_text else None
        self.status.setText("Indexing FM26 asset sets without assigning unproven geometry meanings…")
        try:
            result = self.service.index_library(library_root)
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Index failed", str(exc))
            self.status.setText("Library index failed. Choose the correct FM26 heads folder.")
            return
        self.dataset_status.setPlainText(
            f"Head sets: {result.head_sets}\n"
            f"Face textures: {result.textures}\n"
            f"CFG2 files: {result.cfg2_files}\n"
            f"Comparable geometry records: {result.geometry_records}\n\n"
            + "\n".join(result.warnings)
        )
        self.status.setText("Library inventory complete. Donor matching remains correctly disabled until comparable geometry records exist.")

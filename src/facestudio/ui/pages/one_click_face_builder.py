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
    QListWidget,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from facestudio.match_engine_research.geometry_dataset import (
    GeometryDatasetService,
    HeadGeometryRecord,
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
        self.dataset_service = GeometryDatasetService()
        self.photo: Path | None = None
        self.analysis: PhotoAnalysis | None = None
        self.geometry_records: tuple[HeadGeometryRecord, ...] = ()

        root = QVBoxLayout(self)
        title = QLabel("FM26 Calibrated Geometry Matcher")
        title.setObjectName("PageTitle")
        root.addWidget(title)

        summary = QLabel(
            "Load and correct one portrait, then import a calibrated FM26 head-geometry dataset created from standard front renders or decoded meshes. "
            "FaceStudio can now rank real comparable records, while texture rebuilding remains disabled until the geometry dataset is proven in game."
        )
        summary.setWordWrap(True)
        root.addWidget(summary)

        library_row = QHBoxLayout()
        self.library_path = QLineEdit()
        self.library_path.setPlaceholderText("FM26 heads folder — leave blank for automatic detection")
        browse_library = QPushButton("Choose heads folder")
        browse_library.clicked.connect(self.choose_library)
        index_library = QPushButton("Index FM26 assets")
        index_library.clicked.connect(self.index_library)
        library_row.addWidget(self.library_path, 1)
        library_row.addWidget(browse_library)
        library_row.addWidget(index_library)
        root.addLayout(library_row)

        content = QHBoxLayout()

        source_box = QVBoxLayout()
        source_title = QLabel("1. Correct portrait landmarks")
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
        editor_title = QLabel("2. Review measurements")
        editor_title.setObjectName("SectionTitle")
        editor_box.addWidget(editor_title)
        explanation = QLabel(
            "Select every point and correct its normalised X/Y position. Matching is enabled only after at least one manual correction and a calibrated dataset is loaded."
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
        save_record = QPushButton("Save portrait landmark JSON")
        save_record.clicked.connect(self.save_record)
        editor_box.addWidget(save_record)

        dataset_box = QVBoxLayout()
        dataset_title = QLabel("3. Calibrated FM26 geometry")
        dataset_title.setObjectName("SectionTitle")
        dataset_box.addWidget(dataset_title)
        self.dataset_status = QLabel(
            "No calibrated geometry dataset loaded. Accepted evidence: standardised head renders or decoded mesh measurements. UV textures are rejected."
        )
        self.dataset_status.setWordWrap(True)
        dataset_box.addWidget(self.dataset_status)
        import_dataset = QPushButton("Import calibrated geometry dataset")
        import_dataset.clicked.connect(self.import_dataset)
        dataset_box.addWidget(import_dataset)
        self.match_button = QPushButton("Match corrected portrait to FM26 heads")
        self.match_button.setEnabled(False)
        self.match_button.clicked.connect(self.match_geometry)
        dataset_box.addWidget(self.match_button)
        self.matches = QListWidget()
        self.matches.addItem("No comparable records loaded")
        dataset_box.addWidget(self.matches, 1)
        self.match_details = QTextEdit()
        self.match_details.setReadOnly(True)
        self.match_details.setPlaceholderText("Component differences appear after matching")
        dataset_box.addWidget(self.match_details, 1)
        disabled_export = QPushButton("Texture rebuild/export remains unavailable")
        disabled_export.setEnabled(False)
        dataset_box.addWidget(disabled_export)

        source_widget = QWidget(); source_widget.setLayout(source_box)
        editor_widget = QWidget(); editor_widget.setLayout(editor_box)
        dataset_widget = QWidget(); dataset_widget.setLayout(dataset_box)
        content.addWidget(source_widget, 2)
        content.addWidget(editor_widget, 1)
        content.addWidget(dataset_widget, 1)
        root.addLayout(content, 1)

        self.status = QLabel("Ready. This build performs evidence-backed matching only when calibrated FM geometry records are supplied.")
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
        self.refresh_match_state()
        self.status.setText("Initial landmark estimates loaded. Review and correct the points before matching.")

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
        self.refresh_match_state()
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
        self.status.setText("Indexing FM26 asset coverage without assigning geometry to UV textures…")
        try:
            result = self.service.index_library(library_root)
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Index failed", str(exc))
            self.status.setText("Library index failed. Choose the correct FM26 heads folder.")
            return
        self.dataset_status.setText(
            f"FM asset inventory: {result.head_sets} head sets, {result.textures} textures and {result.cfg2_files} CFG2 files. "
            f"Loaded calibrated geometry records: {len(self.geometry_records)}."
        )
        self.status.setText("FM26 asset inventory complete. Geometry records must still be imported separately.")

    def import_dataset(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(
            self, "Import calibrated FM26 geometry dataset", "", "JSON files (*.json)"
        )
        if not selected:
            return
        try:
            self.geometry_records = self.dataset_service.load(Path(selected))
        except ValueError as exc:
            QMessageBox.critical(self, "Dataset rejected", str(exc))
            return
        render_count = sum(1 for record in self.geometry_records if record.front_render)
        decoded_count = sum(1 for record in self.geometry_records if record.source_type == "decoded-mesh")
        self.dataset_status.setText(
            f"Loaded {len(self.geometry_records)} comparable FM26 geometry records. "
            f"Front renders: {render_count}. Decoded-mesh records: {decoded_count}."
        )
        self.matches.clear()
        self.matches.addItem("Dataset loaded — correct the portrait and run matching")
        self.refresh_match_state()
        self.status.setText("Calibrated geometry dataset loaded and validated.")

    def refresh_match_state(self) -> None:
        enabled = bool(self.geometry_records) and self.analysis is not None and self.analysis.manually_corrected
        self.match_button.setEnabled(enabled)

    def match_geometry(self) -> None:
        if self.analysis is None or not self.analysis.manually_corrected:
            QMessageBox.warning(self, "Corrected portrait required", "Load a portrait and manually correct its landmarks first.")
            return
        try:
            matches = self.dataset_service.match(self.analysis.measurements, self.geometry_records, limit=10)
        except ValueError as exc:
            QMessageBox.critical(self, "Matching failed", str(exc))
            return
        self.matches.clear()
        for index, match in enumerate(matches, start=1):
            evidence = "mesh" if match.source_type == "decoded-mesh" else "render"
            self.matches.addItem(f"{index}. {match.player_id}   {match.score}%   {evidence}   confidence {match.confidence:.2f}")
        best = matches[0]
        details = "\n".join(
            f"{name.replace('_', ' ').title()}: {difference:.4f}"
            for name, difference in best.component_differences.items()
        )
        self.match_details.setPlainText(
            f"Best comparable record: {best.player_id}\n"
            f"Transparent geometry score: {best.score}%\n"
            f"Evidence: {best.source_type}\n"
            f"Record confidence: {best.confidence:.2f}\n\n"
            f"Component differences\n{details}"
        )
        self.status.setText(
            f"Matched against {len(self.geometry_records)} calibrated records. Texture reconstruction remains deliberately disabled."
        )

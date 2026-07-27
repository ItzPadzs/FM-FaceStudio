from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QImageReader
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
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

from facestudio.match_engine_research.geometry_dataset import GeometryDatasetService, HeadGeometryRecord
from facestudio.match_engine_research.one_click_face_builder import LANDMARK_ORDER, OneClickFaceBuilder, PhotoAnalysis
from facestudio.ui.widgets.landmark_editor import LandmarkEditor


class OneClickFaceBuilderPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.service = OneClickFaceBuilder()
        self.dataset_service = GeometryDatasetService()
        self.photo: Path | None = None
        self.analysis: PhotoAnalysis | None = None
        self.geometry_records: tuple[HeadGeometryRecord, ...] = ()
        self._syncing_selection = False

        root = QVBoxLayout(self)
        title = QLabel("FM26 Drag Landmark & Geometry Matcher")
        title.setObjectName("PageTitle")
        root.addWidget(title)

        summary = QLabel(
            "Load one portrait and drag the landmark points directly onto the face. Measurements update instantly. "
            "A calibrated FM26 geometry dataset can then rank comparable donor-head records."
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
        source_title = QLabel("1. Drag portrait landmarks")
        source_title.setObjectName("SectionTitle")
        source_box.addWidget(source_title)
        self.source_preview = LandmarkEditor()
        self.source_preview.landmark_moved.connect(self.drag_landmark)
        self.source_preview.landmark_selected.connect(self.select_landmark)
        source_box.addWidget(self.source_preview, 1)
        choose_photo = QPushButton("Choose photograph")
        choose_photo.clicked.connect(self.choose_photo)
        source_box.addWidget(choose_photo)
        self.photo_status = QLabel("No photograph loaded. Dragging becomes available after selecting a portrait.")
        self.photo_status.setWordWrap(True)
        source_box.addWidget(self.photo_status)

        editor_box = QVBoxLayout()
        editor_title = QLabel("2. Live measurements")
        editor_title.setObjectName("SectionTitle")
        editor_box.addWidget(editor_title)
        explanation = QLabel(
            "Click a green point and drag it onto the correct facial feature. The selected point turns amber. "
            "The list below can also jump directly to a landmark."
        )
        explanation.setWordWrap(True)
        editor_box.addWidget(explanation)
        self.landmark_name = QComboBox()
        self.landmark_name.addItems(LANDMARK_ORDER)
        self.landmark_name.currentTextChanged.connect(self.select_landmark_from_list)
        editor_box.addWidget(self.landmark_name)
        self.selected_status = QLabel("Selected point: none")
        self.selected_status.setWordWrap(True)
        editor_box.addWidget(self.selected_status)
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

        self.status = QLabel("Ready. Load a portrait, then drag at least one landmark to enable calibrated matching.")
        self.status.setWordWrap(True)
        root.addWidget(self.status)

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
        self.source_preview.select_landmark(self.landmark_name.currentText())
        self.refresh_match_state()
        self.status.setText("Initial estimates loaded. Click and drag every point onto the correct facial feature.")

    def refresh_analysis(self) -> None:
        if self.analysis is None or self.photo is None:
            return
        reader = QImageReader(str(self.photo))
        reader.setAutoTransform(True)
        image = reader.read()
        self.source_preview.set_content(image, self.analysis.landmarks)
        correction = "drag-corrected" if self.analysis.manually_corrected else "initial estimates only"
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

    def drag_landmark(self, name: str, x: float, y: float) -> None:
        if self.analysis is None:
            return
        self.analysis = self.service.update_landmark(self.analysis, name, x, y)
        self.refresh_analysis()
        self.select_landmark(name)
        self.refresh_match_state()
        self.status.setText(f"Moved {name.replace('_', ' ')}. Measurements recalculated instantly.")

    def select_landmark(self, name: str) -> None:
        self.selected_status.setText(f"Selected point: {name.replace('_', ' ')}")
        if self.landmark_name.currentText() != name:
            self._syncing_selection = True
            self.landmark_name.setCurrentText(name)
            self._syncing_selection = False

    def select_landmark_from_list(self, name: str) -> None:
        if self._syncing_selection:
            return
        self.source_preview.select_landmark(name)
        self.selected_status.setText(f"Selected point: {name.replace('_', ' ')}")

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
        selected, _ = QFileDialog.getOpenFileName(self, "Import calibrated FM26 geometry dataset", "", "JSON files (*.json)")
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
        self.matches.addItem("Dataset loaded — drag-correct the portrait and run matching")
        self.refresh_match_state()
        self.status.setText("Calibrated geometry dataset loaded and validated.")

    def refresh_match_state(self) -> None:
        enabled = bool(self.geometry_records) and self.analysis is not None and self.analysis.manually_corrected
        self.match_button.setEnabled(enabled)

    def match_geometry(self) -> None:
        if self.analysis is None or not self.analysis.manually_corrected:
            QMessageBox.warning(self, "Corrected portrait required", "Load a portrait and drag at least one landmark first.")
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

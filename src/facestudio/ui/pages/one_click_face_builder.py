from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QImageReader, QPixmap
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

from facestudio.match_engine_research.donor_selection import DonorSelectionService, LockedDonor
from facestudio.match_engine_research.geometry_dataset import GeometryDatasetService, GeometryMatch, HeadGeometryRecord
from facestudio.match_engine_research.one_click_face_builder import LANDMARK_ORDER, OneClickFaceBuilder, PhotoAnalysis
from facestudio.ui.dialogs.render_dataset_builder_dialog import RenderDatasetBuilderDialog
from facestudio.ui.widgets.landmark_editor import LandmarkEditor


class OneClickFaceBuilderPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.service = OneClickFaceBuilder()
        self.dataset_service = GeometryDatasetService()
        self.selection_service = DonorSelectionService()
        self.photo: Path | None = None
        self.analysis: PhotoAnalysis | None = None
        self.geometry_records: tuple[HeadGeometryRecord, ...] = ()
        self.current_matches: tuple[GeometryMatch, ...] = ()
        self.locked_donor: LockedDonor | None = None
        self._syncing_selection = False

        root = QVBoxLayout(self)
        title = QLabel("FM26 Donor Review & Lock")
        title.setObjectName("PageTitle")
        root.addWidget(title)
        summary = QLabel(
            "Drag-correct one portrait, match it against the calibrated FM26 geometry dataset, inspect each candidate render, then explicitly lock the donor head used by the next reconstruction stage."
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
        source_title = QLabel("1. Correct portrait")
        source_title.setObjectName("SectionTitle")
        source_box.addWidget(source_title)
        self.source_preview = LandmarkEditor()
        self.source_preview.landmark_moved.connect(self.drag_landmark)
        self.source_preview.landmark_selected.connect(self.select_landmark)
        source_box.addWidget(self.source_preview, 1)
        choose_photo = QPushButton("Choose photograph")
        choose_photo.clicked.connect(self.choose_photo)
        source_box.addWidget(choose_photo)
        self.photo_status = QLabel("No photograph loaded.")
        self.photo_status.setWordWrap(True)
        source_box.addWidget(self.photo_status)

        editor_box = QVBoxLayout()
        editor_title = QLabel("2. Measurements")
        editor_title.setObjectName("SectionTitle")
        editor_box.addWidget(editor_title)
        self.landmark_name = QComboBox()
        self.landmark_name.addItems(LANDMARK_ORDER)
        self.landmark_name.currentTextChanged.connect(self.select_landmark_from_list)
        editor_box.addWidget(self.landmark_name)
        self.selected_status = QLabel("Selected point: none")
        editor_box.addWidget(self.selected_status)
        self.measurements = QTextEdit()
        self.measurements.setReadOnly(True)
        self.measurements.setPlaceholderText("Measurements appear after loading a photograph")
        editor_box.addWidget(self.measurements, 1)
        save_record = QPushButton("Save portrait landmark JSON")
        save_record.clicked.connect(self.save_record)
        editor_box.addWidget(save_record)

        match_box = QVBoxLayout()
        match_title = QLabel("3. Match and review")
        match_title.setObjectName("SectionTitle")
        match_box.addWidget(match_title)
        self.dataset_status = QLabel("Build or import a calibrated render dataset.")
        self.dataset_status.setWordWrap(True)
        match_box.addWidget(self.dataset_status)
        build_dataset = QPushButton("Build dataset from calibrated front renders")
        build_dataset.clicked.connect(self.open_dataset_builder)
        match_box.addWidget(build_dataset)
        import_dataset = QPushButton("Import calibrated geometry dataset")
        import_dataset.clicked.connect(self.import_dataset)
        match_box.addWidget(import_dataset)
        self.match_button = QPushButton("Match portrait to FM26 heads")
        self.match_button.setEnabled(False)
        self.match_button.clicked.connect(self.match_geometry)
        match_box.addWidget(self.match_button)
        self.matches = QListWidget()
        self.matches.currentRowChanged.connect(self.review_match)
        self.matches.addItem("No comparable records loaded")
        match_box.addWidget(self.matches, 1)

        review_box = QVBoxLayout()
        review_title = QLabel("4. Review and lock donor")
        review_title.setObjectName("SectionTitle")
        review_box.addWidget(review_title)
        previews = QHBoxLayout()
        self.front_preview = self._preview("Front render")
        self.side_preview = self._preview("Side render\noptional")
        previews.addWidget(self.front_preview, 1)
        previews.addWidget(self.side_preview, 1)
        review_box.addLayout(previews, 1)
        self.match_details = QTextEdit()
        self.match_details.setReadOnly(True)
        self.match_details.setPlaceholderText("Select a match to inspect its evidence and component differences")
        review_box.addWidget(self.match_details, 1)
        self.lock_button = QPushButton("Lock selected donor head")
        self.lock_button.setEnabled(False)
        self.lock_button.clicked.connect(self.lock_selected_donor)
        review_box.addWidget(self.lock_button)
        self.export_selection = QPushButton("Export locked donor manifest")
        self.export_selection.setEnabled(False)
        self.export_selection.clicked.connect(self.export_locked_donor)
        review_box.addWidget(self.export_selection)
        self.lock_status = QLabel("No donor locked. Texture reconstruction remains unavailable.")
        self.lock_status.setWordWrap(True)
        review_box.addWidget(self.lock_status)

        source_widget = QWidget(); source_widget.setLayout(source_box)
        editor_widget = QWidget(); editor_widget.setLayout(editor_box)
        match_widget = QWidget(); match_widget.setLayout(match_box)
        review_widget = QWidget(); review_widget.setLayout(review_box)
        content.addWidget(source_widget, 2)
        content.addWidget(editor_widget, 1)
        content.addWidget(match_widget, 1)
        content.addWidget(review_widget, 2)
        root.addLayout(content, 1)
        self.status = QLabel("Ready. The best score is a recommendation only; you must review and lock the donor explicitly.")
        self.status.setWordWrap(True)
        root.addWidget(self.status)

    @staticmethod
    def _preview(text: str) -> QLabel:
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setMinimumSize(180, 220)
        label.setWordWrap(True)
        return label

    def choose_library(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Choose FM26 heads folder")
        if selected:
            self.library_path.setText(selected)

    def choose_photo(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(self, "Choose one front-facing photograph", "", "Images (*.png *.jpg *.jpeg *.webp *.bmp)")
        if not selected:
            return
        self.photo = Path(selected)
        try:
            self.analysis = self.service.analyse_photo(self.photo)
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Photo error", str(exc)); self.photo = None; self.analysis = None; return
        self.current_matches = ()
        self.locked_donor = None
        self.refresh_analysis()
        self.landmark_name.setCurrentIndex(0)
        self.source_preview.select_landmark(self.landmark_name.currentText())
        self.refresh_match_state()
        self.clear_review()
        self.status.setText("Initial estimates loaded. Drag every point onto the correct facial feature.")

    def refresh_analysis(self) -> None:
        if self.analysis is None or self.photo is None:
            return
        reader = QImageReader(str(self.photo)); reader.setAutoTransform(True)
        self.source_preview.set_content(reader.read(), self.analysis.landmarks)
        correction = "drag-corrected" if self.analysis.manually_corrected else "initial estimates only"
        self.photo_status.setText(f"Quality {self.analysis.quality_score}% · {correction}\n" + " ".join(self.analysis.warnings))
        values = self.analysis.measurements
        self.measurements.setPlainText(
            "Normalised measurements\n\n"
            f"Face width: {values.face_width:.3f}\nFace height: {values.face_height:.3f}\n"
            f"Eye spacing: {values.eye_spacing:.3f}\nNose length: {values.nose_length:.3f}\n"
            f"Mouth width: {values.mouth_width:.3f}\nJaw width: {values.jaw_width:.3f}\n"
            f"Chin length: {values.chin_length:.3f}\nSymmetry: {values.symmetry:.3f}"
        )

    def drag_landmark(self, name: str, x: float, y: float) -> None:
        if self.analysis is None:
            return
        self.analysis = self.service.update_landmark(self.analysis, name, x, y)
        self.current_matches = ()
        self.locked_donor = None
        self.refresh_analysis(); self.select_landmark(name); self.refresh_match_state(); self.clear_review()
        self.status.setText(f"Moved {name.replace('_', ' ')}. Previous matches cleared because the geometry changed.")

    def select_landmark(self, name: str) -> None:
        self.selected_status.setText(f"Selected point: {name.replace('_', ' ')}")
        if self.landmark_name.currentText() != name:
            self._syncing_selection = True; self.landmark_name.setCurrentText(name); self._syncing_selection = False

    def select_landmark_from_list(self, name: str) -> None:
        if not self._syncing_selection:
            self.source_preview.select_landmark(name)
            self.selected_status.setText(f"Selected point: {name.replace('_', ' ')}")

    def save_record(self) -> None:
        if self.analysis is None:
            QMessageBox.warning(self, "Nothing to save", "Choose and review a photograph first."); return
        selected, _ = QFileDialog.getSaveFileName(self, "Save landmark record", "facestudio-landmarks.json", "JSON files (*.json)")
        if not selected:
            return
        try:
            destination = self.service.save_analysis(self.analysis, Path(selected))
        except OSError as exc:
            QMessageBox.critical(self, "Save failed", str(exc)); return
        QMessageBox.information(self, "Record saved", f"Saved to:\n{destination}")

    def index_library(self) -> None:
        root_text = self.library_path.text().strip(); library_root = Path(root_text).expanduser() if root_text else None
        try:
            result = self.service.index_library(library_root)
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Index failed", str(exc)); return
        self.dataset_status.setText(
            f"FM assets: {result.head_sets} head sets, {result.textures} textures and {result.cfg2_files} CFG2 files. "
            f"Calibrated records loaded: {len(self.geometry_records)}."
        )

    def open_dataset_builder(self) -> None:
        dialog = RenderDatasetBuilderDialog(self)
        dialog.exec()
        self.status.setText("Dataset Builder closed. Import its exported JSON to review and lock donors.")

    def import_dataset(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(self, "Import calibrated FM26 geometry dataset", "", "JSON files (*.json)")
        if not selected:
            return
        try:
            self.geometry_records = self.dataset_service.load(Path(selected))
        except ValueError as exc:
            QMessageBox.critical(self, "Dataset rejected", str(exc)); return
        self.current_matches = ()
        self.locked_donor = None
        render_count = sum(1 for record in self.geometry_records if record.front_render)
        self.dataset_status.setText(f"Loaded {len(self.geometry_records)} calibrated records with {render_count} front renders.")
        self.matches.clear(); self.matches.addItem("Dataset loaded — correct the portrait and run matching")
        self.clear_review(); self.refresh_match_state()

    def refresh_match_state(self) -> None:
        self.match_button.setEnabled(bool(self.geometry_records) and self.analysis is not None and self.analysis.manually_corrected)

    def match_geometry(self) -> None:
        if self.analysis is None or not self.analysis.manually_corrected:
            QMessageBox.warning(self, "Corrected portrait required", "Load a portrait and drag at least one landmark first."); return
        try:
            self.current_matches = self.dataset_service.match(self.analysis.measurements, self.geometry_records, limit=10)
        except ValueError as exc:
            QMessageBox.critical(self, "Matching failed", str(exc)); return
        self.locked_donor = None
        self.matches.clear()
        for index, match in enumerate(self.current_matches, start=1):
            evidence = "mesh" if match.source_type == "decoded-mesh" else "render"
            self.matches.addItem(f"{index}. {match.player_id}   {match.score}%   {evidence}   confidence {match.confidence:.2f}")
        self.matches.setCurrentRow(0)
        self.export_selection.setEnabled(False)
        self.lock_status.setText("Review the candidate renders and explicitly lock one donor.")
        self.status.setText(f"Matched against {len(self.geometry_records)} calibrated records. Highest score is not automatically accepted.")

    def review_match(self, row: int) -> None:
        if row < 0 or row >= len(self.current_matches):
            self.lock_button.setEnabled(False)
            return
        match = self.current_matches[row]
        details = "\n".join(f"{name.replace('_', ' ').title()}: {difference:.4f}" for name, difference in match.component_differences.items())
        self.match_details.setPlainText(
            f"Candidate donor: {match.player_id}\nGeometry score: {match.score}%\n"
            f"Evidence: {match.source_type}\nRecord confidence: {match.confidence:.2f}\n\nComponent differences\n{details}"
        )
        self.show_render(self.front_preview, match.front_render, "No front render available")
        self.show_render(self.side_preview, match.side_render, "No side render available")
        self.lock_button.setEnabled(match.score > 0)

    @staticmethod
    def show_render(label: QLabel, render_path: str | None, missing_text: str) -> None:
        label.setPixmap(QPixmap())
        if not render_path or not Path(render_path).is_file():
            label.setText(missing_text)
            return
        pixmap = QPixmap(render_path)
        if pixmap.isNull():
            label.setText("Render could not be decoded")
            return
        label.setText("")
        label.setPixmap(pixmap.scaled(label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def lock_selected_donor(self) -> None:
        row = self.matches.currentRow()
        if self.analysis is None or row < 0 or row >= len(self.current_matches):
            QMessageBox.warning(self, "Donor required", "Select a reviewed geometry match first."); return
        try:
            self.locked_donor = self.selection_service.lock(self.current_matches[row], self.analysis.measurements)
        except ValueError as exc:
            QMessageBox.critical(self, "Cannot lock donor", str(exc)); return
        self.export_selection.setEnabled(True)
        self.lock_status.setText(
            f"Locked donor {self.locked_donor.player_id} at {self.locked_donor.score}% geometry similarity. "
            "This selection is now ready for the landmark-driven texture reconstruction stage."
        )
        self.status.setText(f"Donor {self.locked_donor.player_id} locked. Export the manifest before starting texture reconstruction.")

    def export_locked_donor(self) -> None:
        if self.locked_donor is None:
            QMessageBox.warning(self, "No locked donor", "Review and lock a donor first."); return
        selected, _ = QFileDialog.getSaveFileName(
            self, "Export locked donor manifest", f"facestudio-donor-{self.locked_donor.player_id}.json", "JSON files (*.json)"
        )
        if not selected:
            return
        try:
            destination = self.selection_service.save(self.locked_donor, Path(selected))
        except OSError as exc:
            QMessageBox.critical(self, "Export failed", str(exc)); return
        QMessageBox.information(self, "Donor manifest exported", f"Saved to:\n{destination}")

    def clear_review(self) -> None:
        self.front_preview.setPixmap(QPixmap()); self.front_preview.setText("Front render")
        self.side_preview.setPixmap(QPixmap()); self.side_preview.setText("Side render\noptional")
        self.match_details.clear()
        self.lock_button.setEnabled(False)
        self.export_selection.setEnabled(False)
        self.lock_status.setText("No donor locked. Texture reconstruction remains unavailable.")

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QComboBox, QDialog, QFileDialog, QLabel, QMessageBox, QPushButton, QVBoxLayout

from facestudio.match_engine_research.one_click_face_builder import LANDMARK_ORDER
from facestudio.match_engine_research.uv_calibration import UVCalibration, UVCalibrationService
from facestudio.ui.widgets.landmark_editor import LandmarkEditor


class UVCalibrationDialog(QDialog):
    def __init__(self, player_id: str, heads_root: Path, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Calibrate donor UV anchors — {player_id}")
        self.resize(900, 760)
        self.service = UVCalibrationService()
        self.calibration: UVCalibration | None = None

        root = QVBoxLayout(self)
        title = QLabel(f"Donor {player_id} UV anchor calibration")
        title.setObjectName("PageTitle")
        root.addWidget(title)
        help_text = QLabel(
            "This texture is an FM UV map, not a face photograph. Drag each named anchor to the texture location that represents that feature. "
            "The saved calibration will drive the next triangulated reconstruction stage."
        )
        help_text.setWordWrap(True)
        root.addWidget(help_text)

        self.editor = LandmarkEditor()
        self.editor.landmark_moved.connect(self.move_anchor)
        self.editor.landmark_selected.connect(self.select_anchor)
        root.addWidget(self.editor, 1)
        self.anchor_name = QComboBox(); self.anchor_name.addItems(LANDMARK_ORDER)
        self.anchor_name.currentTextChanged.connect(self.editor.select_landmark)
        root.addWidget(self.anchor_name)
        self.status = QLabel("Loading donor texture…"); self.status.setWordWrap(True)
        root.addWidget(self.status)
        save = QPushButton("Save reviewed UV calibration")
        save.clicked.connect(self.save)
        root.addWidget(save)

        try:
            self.calibration = self.service.create(heads_root, player_id)
            image = self.service.read_texture(Path(self.calibration.texture_path))
            self.editor.set_content(image, self.calibration.anchors)
            self.editor.select_landmark(LANDMARK_ORDER[0])
            self.status.setText("0 of 12 anchors reviewed. Drag every anchor before the reconstruction stage is considered calibrated.")
        except ValueError as exc:
            QMessageBox.critical(self, "UV calibration unavailable", str(exc))
            self.reject()

    def move_anchor(self, name: str, x: float, y: float) -> None:
        if self.calibration is None:
            return
        self.calibration = self.service.update(self.calibration, name, x, y)
        image = self.service.read_texture(Path(self.calibration.texture_path))
        self.editor.set_content(image, self.calibration.anchors)
        self.editor.select_landmark(name)
        self.anchor_name.setCurrentText(name)
        count = len(self.calibration.corrected_names)
        suffix = "Calibration complete." if self.calibration.complete else "Review all anchors before reconstruction."
        self.status.setText(f"{count} of {len(LANDMARK_ORDER)} anchors reviewed. {suffix}")

    def select_anchor(self, name: str) -> None:
        self.anchor_name.setCurrentText(name)

    def save(self) -> None:
        if self.calibration is None:
            return
        selected, _ = QFileDialog.getSaveFileName(
            self, "Save donor UV calibration", f"facestudio-uv-{self.calibration.player_id}.json", "JSON files (*.json)"
        )
        if not selected:
            return
        try:
            destination = self.service.save(self.calibration, Path(selected))
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Save failed", str(exc)); return
        QMessageBox.information(self, "UV calibration saved", f"Saved to:\n{destination}")

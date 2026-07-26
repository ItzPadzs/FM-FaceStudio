from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMessageBox,
    QPushButton,
    QSlider,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from facestudio.image_studio.service import ImageRecord, ImageStudioService


class ImageStudioPage(QWidget):
    def __init__(self, service: ImageStudioService) -> None:
        super().__init__()
        self.service = service
        self.records: list[ImageRecord] = []
        self.current: ImageRecord | None = None

        root = QVBoxLayout(self)
        heading = QLabel("Image Preparation Studio")
        heading.setObjectName("PageTitle")
        root.addWidget(heading)
        description = QLabel(
            "Import, inspect, crop, rotate, enhance and export user-supplied images in standard formats. "
            "Edits are stored as transparent FaceStudio metadata and never overwrite the source file."
        )
        description.setWordWrap(True)
        root.addWidget(description)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._library_tab(), "Library")
        self.tabs.addTab(self._editor_tab(), "Crop & Enhance")
        self.tabs.addTab(self._batch_tab(), "Batch & Export")
        root.addWidget(self.tabs, 1)
        self.refresh_library()

    def _library_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        buttons = QHBoxLayout()
        import_files = QPushButton("Import images")
        import_files.clicked.connect(self.import_files)
        import_folder = QPushButton("Import folder")
        import_folder.clicked.connect(self.import_folder)
        remove = QPushButton("Remove selected record")
        remove.clicked.connect(self.remove_selected)
        refresh = QPushButton("Refresh")
        refresh.clicked.connect(self.refresh_library)
        for button in (import_files, import_folder, remove, refresh):
            buttons.addWidget(button)
        buttons.addStretch()
        layout.addLayout(buttons)

        self.library_table = QTableWidget(0, 7)
        self.library_table.setHorizontalHeaderLabels(
            ["Name", "Resolution", "Quality", "Issues", "Crop", "Export", "Source"]
        )
        self.library_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.library_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.library_table.itemSelectionChanged.connect(self.select_from_table)
        layout.addWidget(self.library_table, 1)
        return page

    def _editor_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        splitter = QSplitter()

        preview_area = QWidget()
        preview_layout = QVBoxLayout(preview_area)
        self.preview_name = QLabel("Select an image from the Library tab")
        self.preview_name.setObjectName("SectionTitle")
        preview_layout.addWidget(self.preview_name)
        self.preview = QLabel("No image selected")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumSize(420, 420)
        self.preview.setStyleSheet("border: 1px solid palette(mid); padding: 8px;")
        preview_layout.addWidget(self.preview, 1)
        splitter.addWidget(preview_area)

        controls = QWidget()
        form = QFormLayout(controls)
        self.crop_mode = QComboBox()
        self.crop_mode.addItems(["Original", "Square portrait", "Thumbnail", "HD portrait"])
        self.rotation = QSpinBox()
        self.rotation.setRange(-180, 180)
        self.rotation.setSingleStep(1)
        self.brightness = self._slider(-100, 100)
        self.contrast = self._slider(-100, 100)
        self.saturation = self._slider(-100, 100)
        self.background = QComboBox()
        self.background.addItems(["Original", "White", "Grey", "Black"])
        form.addRow("Crop preset", self.crop_mode)
        form.addRow("Rotation", self.rotation)
        form.addRow("Brightness", self.brightness)
        form.addRow("Contrast", self.contrast)
        form.addRow("Saturation", self.saturation)
        form.addRow("Background canvas", self.background)
        apply_button = QPushButton("Apply non-destructive settings")
        apply_button.clicked.connect(self.apply_settings)
        reset_button = QPushButton("Reset settings")
        reset_button.clicked.connect(self.reset_settings)
        form.addRow(apply_button)
        form.addRow(reset_button)
        self.quality_text = QTextEdit()
        self.quality_text.setReadOnly(True)
        self.quality_text.setMaximumHeight(150)
        form.addRow("Quality inspector", self.quality_text)
        splitter.addWidget(controls)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter, 1)
        return page

    def _batch_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        form = QFormLayout()
        self.output_size = QComboBox()
        self.output_size.addItems(["180", "250", "512", "1024"])
        self.output_size.setCurrentText("250")
        self.output_format = QComboBox()
        self.output_format.addItems(["PNG", "JPG", "WEBP"])
        form.addRow("Output size", self.output_size)
        form.addRow("Output format", self.output_format)
        layout.addLayout(form)

        pipeline = QLabel("Pipeline: load source → rotate → centre crop → enhance → resize → encode → JSON sidecar")
        pipeline.setWordWrap(True)
        layout.addWidget(pipeline)
        self.batch_list = QListWidget()
        layout.addWidget(self.batch_list, 1)

        buttons = QHBoxLayout()
        export_current = QPushButton("Export current")
        export_current.clicked.connect(self.export_current)
        export_all = QPushButton("Export all")
        export_all.clicked.connect(self.export_all)
        buttons.addWidget(export_current)
        buttons.addWidget(export_all)
        buttons.addStretch()
        layout.addLayout(buttons)
        return page

    def _slider(self, minimum: int, maximum: int) -> QSlider:
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(minimum, maximum)
        slider.setValue(0)
        slider.setTickInterval(25)
        return slider

    def import_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self, "Import images", "", "Images (*.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff)"
        )
        if files:
            self._import([Path(item) for item in files])

    def import_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Import image folder")
        if folder:
            self._import([Path(folder)])

    def _import(self, paths: list[Path]) -> None:
        count, errors = self.service.import_paths(paths)
        self.refresh_library()
        message = f"Imported {count} new image(s)."
        if errors:
            message += "\n\n" + "\n".join(errors[:10])
        QMessageBox.information(self, "Image import", message)

    def refresh_library(self) -> None:
        self.records = self.service.load()
        self.library_table.setRowCount(len(self.records))
        self.batch_list.clear()
        for row, record in enumerate(self.records):
            values = [
                record.name,
                f"{record.width} × {record.height}",
                f"{record.quality_score}%",
                ", ".join(record.issues) or "None",
                record.crop_mode,
                record.exported_path or "Not exported",
                record.source_path,
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, record.id)
                self.library_table.setItem(row, column, item)
            self.batch_list.addItem(f"{record.name} — {record.quality_score}% — {record.crop_mode}")
        self.library_table.resizeColumnsToContents()

    def select_from_table(self) -> None:
        row = self.library_table.currentRow()
        if row < 0 or row >= len(self.records):
            return
        self.current = self.records[row]
        self.load_controls()
        self.tabs.setCurrentIndex(1)

    def load_controls(self) -> None:
        if self.current is None:
            return
        record = self.current
        self.preview_name.setText(record.name)
        self.crop_mode.setCurrentText(record.crop_mode)
        self.rotation.setValue(record.rotation)
        self.brightness.setValue(record.brightness)
        self.contrast.setValue(record.contrast)
        self.saturation.setValue(record.saturation)
        self.background.setCurrentText(record.background)
        issues = "\n".join(f"• {item}" for item in record.issues) or "No basic file-quality warnings."
        self.quality_text.setPlainText(f"Score: {record.quality_score}%\n{issues}")
        self.refresh_preview()

    def refresh_preview(self) -> None:
        if self.current is None:
            return
        image = self.service.render(self.current)
        if image.isNull():
            self.preview.setText("Source image is missing or unreadable")
            return
        pixmap = QPixmap.fromImage(image).scaled(
            560, 560, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        )
        self.preview.setPixmap(pixmap)

    def apply_settings(self) -> None:
        if self.current is None:
            QMessageBox.warning(self, "Image Studio", "Select an image first.")
            return
        record = self.current
        record.crop_mode = self.crop_mode.currentText()
        record.rotation = self.rotation.value()
        record.brightness = self.brightness.value()
        record.contrast = self.contrast.value()
        record.saturation = self.saturation.value()
        record.background = self.background.currentText()
        record.history.append("Updated crop and enhancement settings")
        self.service.update(record)
        self.refresh_preview()
        self.refresh_library()

    def reset_settings(self) -> None:
        if self.current is None:
            return
        self.crop_mode.setCurrentText("Original")
        self.rotation.setValue(0)
        self.brightness.setValue(0)
        self.contrast.setValue(0)
        self.saturation.setValue(0)
        self.background.setCurrentText("Original")
        self.apply_settings()

    def remove_selected(self) -> None:
        row = self.library_table.currentRow()
        if row < 0 or row >= len(self.records):
            return
        self.service.remove(self.records[row].id)
        self.current = None
        self.preview.clear()
        self.refresh_library()

    def _prepare_output(self, record: ImageRecord) -> None:
        record.output_size = int(self.output_size.currentText())
        record.output_format = self.output_format.currentText()
        self.service.update(record)

    def export_current(self) -> None:
        if self.current is None:
            QMessageBox.warning(self, "Export", "Select an image first.")
            return
        folder = QFileDialog.getExistingDirectory(self, "Choose export folder")
        if not folder:
            return
        try:
            self._prepare_output(self.current)
            target = self.service.export(self.current, Path(folder))
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Export failed", str(exc))
            return
        self.refresh_library()
        QMessageBox.information(self, "Export complete", f"Saved {target}")

    def export_all(self) -> None:
        if not self.records:
            return
        folder = QFileDialog.getExistingDirectory(self, "Choose batch export folder")
        if not folder:
            return
        for record in self.records:
            self._prepare_output(record)
        completed, errors = self.service.batch_export(self.records, Path(folder))
        self.refresh_library()
        message = f"Exported {completed} image(s)."
        if errors:
            message += "\n\n" + "\n".join(errors[:10])
        QMessageBox.information(self, "Batch export", message)

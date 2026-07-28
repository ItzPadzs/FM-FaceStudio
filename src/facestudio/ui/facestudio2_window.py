from __future__ import annotations

from pathlib import Path
import traceback

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QFrame, QGridLayout, QHBoxLayout, QLabel,
    QMainWindow, QMessageBox, QProgressBar, QPushButton, QScrollArea,
    QSizePolicy, QVBoxLayout, QWidget,
)

from facestudio.facestudio2_pipeline import FaceStudio2Pipeline
from facestudio.utils.config import AppConfig
from facestudio.version import APP_VERSION


class FaceStudio2Window(QMainWindow):
    """Production-style one-photo dashboard with genuine per-stage previews."""

    STAGES = (
        ("1. Detect", 5),
        ("2. Align", 20),
        ("3. Donor", 25),
        ("4. Prepare", 40),
        ("5. Eyes", 55),
        ("6. Mid Face", 70),
        ("7. Jaw", 82),
        ("8. Refine", 95),
        ("9. Finalize", 100),
    )

    def __init__(self, config: AppConfig, config_path: Path) -> None:
        super().__init__()
        self.config = config
        self.config_path = config_path
        self.output_dir = config_path.parent / "generated-head-textures"
        self.photo: Path | None = None
        self.index_path: Path | None = None
        self.pipeline: FaceStudio2Pipeline | None = None
        self.busy = False
        self.stage_labels: list[QLabel] = []
        self.stage_dots: list[QLabel] = []
        self.preview_cards: list[tuple[QLabel, QLabel]] = []

        self.setWindowTitle(f"FM FaceStudio — {APP_VERSION}")
        self.resize(1540, 960)
        self.setMinimumSize(1180, 760)
        self.setStyleSheet(self._stylesheet())
        self._build_ui()

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self._sidebar())

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        page = QWidget()
        self.page_layout = QVBoxLayout(page)
        self.page_layout.setContentsMargins(34, 24, 34, 24)
        self.page_layout.setSpacing(14)
        scroll.setWidget(page)
        outer.addWidget(scroll, 1)

        title = QLabel("Create a Head Texture From One Photograph")
        title.setObjectName("PageTitle")
        subtitle = QLabel(
            "FaceStudio finds the closest indexed FM donor and visibly builds the texture region by region. "
            "Every thumbnail below is a real preview written by the active generation engine."
        )
        subtitle.setWordWrap(True)
        subtitle.setObjectName("Muted")
        self.page_layout.addWidget(title)
        self.page_layout.addWidget(subtitle)
        self.page_layout.addWidget(self._timeline())

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(True)
        self.progress.setFormat("Ready")
        self.page_layout.addWidget(self.progress)

        self.status = QLabel("Select a donor index, then upload a clear front-facing portrait.")
        self.status.setObjectName("Status")
        self.status.setWordWrap(True)
        self.page_layout.addWidget(self.status)

        previews = QHBoxLayout()
        previews.setSpacing(16)
        self.source_preview = self._large_preview(previews, "Source Photo", "ALIGNED", "Upload a portrait")
        self.texture_preview = self._large_preview(previews, "Generated Head Texture", "LIVE", "Generation preview")
        self.page_layout.addLayout(previews, 1)

        self.page_layout.addWidget(self._preview_strip())

        footer = QFrame()
        footer.setObjectName("Card")
        fl = QHBoxLayout(footer)
        self.footer_icon = QLabel("●")
        self.footer_icon.setObjectName("ReadyDot")
        self.footer_text = QLabel("One-click mode is ready. Generation begins immediately after portrait upload.")
        self.footer_text.setWordWrap(True)
        fl.addWidget(self.footer_icon)
        fl.addWidget(self.footer_text, 1)
        self.generate_button = QPushButton("⚡ Generate Again")
        self.generate_button.clicked.connect(self.start_generation)
        fl.addWidget(self.generate_button)
        self.page_layout.addWidget(footer)

    def _sidebar(self) -> QWidget:
        side = QFrame()
        side.setObjectName("Sidebar")
        side.setFixedWidth(255)
        layout = QVBoxLayout(side)
        layout.setContentsMargins(20, 24, 20, 20)
        layout.setSpacing(12)

        brand = QLabel("FM FaceStudio")
        brand.setObjectName("Brand")
        layout.addWidget(brand)
        version = QLabel("FACESTUDIO 2.0\nLIVE UV PROTOTYPE")
        version.setObjectName("AccentText")
        layout.addWidget(version)

        self.upload_button = QPushButton("✦  Upload Photo")
        self.upload_button.setObjectName("Primary")
        self.upload_button.clicked.connect(self.choose_photo)
        layout.addWidget(self.upload_button)

        self.photo_card = QLabel("No portrait loaded")
        self.photo_card.setWordWrap(True)
        self.photo_card.setObjectName("MiniCard")
        self.photo_card.setMinimumHeight(66)
        layout.addWidget(self.photo_card)

        self.index_button = QPushButton("Choose Donor Index")
        self.index_button.clicked.connect(self.choose_index)
        layout.addWidget(self.index_button)

        open_output = QPushButton("Open Output Folder")
        open_output.clicked.connect(self.open_output_folder)
        layout.addWidget(open_output)

        layout.addSpacing(8)
        pipeline_title = QLabel("GENERATION PIPELINE")
        pipeline_title.setObjectName("SectionTitle")
        layout.addWidget(pipeline_title)
        for name, _ in self.STAGES:
            row = QHBoxLayout()
            dot = QLabel("○")
            dot.setObjectName("StageIdle")
            label = QLabel(name)
            label.setObjectName("StageText")
            row.addWidget(dot)
            row.addWidget(label, 1)
            self.stage_dots.append(dot)
            self.stage_labels.append(label)
            layout.addLayout(row)

        layout.addStretch()
        engine = QFrame()
        engine.setObjectName("Card")
        el = QVBoxLayout(engine)
        el.addWidget(QLabel("ENGINE STATUS"))
        self.engine_status = QLabel("Regional transfer engine\nWaiting for donor index")
        self.engine_status.setObjectName("Muted")
        self.engine_status.setWordWrap(True)
        el.addWidget(self.engine_status)
        layout.addWidget(engine)
        return side

    def _timeline(self) -> QWidget:
        frame = QFrame()
        frame.setObjectName("Timeline")
        grid = QGridLayout(frame)
        grid.setContentsMargins(10, 10, 10, 8)
        grid.setHorizontalSpacing(3)
        for column, (name, _) in enumerate(self.STAGES):
            dot = QLabel("○")
            dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
            dot.setObjectName("TopStageIdle")
            text = QLabel(name)
            text.setAlignment(Qt.AlignmentFlag.AlignCenter)
            text.setObjectName("TopStageText")
            grid.addWidget(dot, 0, column)
            grid.addWidget(text, 1, column)
        self.top_timeline = frame
        return frame

    def _large_preview(self, parent: QHBoxLayout, title: str, badge: str, empty: str) -> QLabel:
        card = QFrame()
        card.setObjectName("Card")
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout = QVBoxLayout(card)
        header = QHBoxLayout()
        header.addWidget(QLabel(title))
        badge_label = QLabel(badge)
        badge_label.setObjectName("Badge")
        header.addWidget(badge_label)
        header.addStretch()
        layout.addLayout(header)
        preview = QLabel(empty)
        preview.setObjectName("Preview")
        preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview.setMinimumHeight(390)
        layout.addWidget(preview, 1)
        parent.addWidget(card, 1)
        return preview

    def _preview_strip(self) -> QWidget:
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.addWidget(QLabel("Generation Progress — Real Engine Frames"))
        row = QHBoxLayout()
        labels = ("Donor", "Aligned", "Eyes", "Mid Face", "Jaw", "Refine", "Complete")
        for label in labels:
            cell = QVBoxLayout()
            image = QLabel("—")
            image.setObjectName("Thumb")
            image.setAlignment(Qt.AlignmentFlag.AlignCenter)
            image.setMinimumSize(120, 88)
            caption = QLabel(label)
            caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
            caption.setObjectName("Muted")
            cell.addWidget(image)
            cell.addWidget(caption)
            row.addLayout(cell, 1)
            self.preview_cards.append((image, caption))
        layout.addLayout(row)
        return card

    def choose_index(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self, "Choose donor-asset-index.json", "", "FaceStudio donor index (donor-asset-index.json);;JSON (*.json)"
        )
        if not filename:
            return
        try:
            self.index_path = Path(filename)
            self.pipeline = FaceStudio2Pipeline(self.index_path)
            self.index_button.setText(f"Index: {self.index_path.parent.name}")
            self.engine_status.setText("Regional transfer engine ACTIVE\nAutomatic donor selection enabled")
            self.status.setText("Donor index loaded. Upload a portrait to start one-click generation.")
            if self.photo:
                self.start_generation()
        except Exception as exc:
            self.pipeline = None
            QMessageBox.critical(self, "Invalid donor index", str(exc))

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
            self.status.setText("Portrait ready. Choose the donor index to begin generation.")
            self.choose_index()
        else:
            self.start_generation()

    def start_generation(self) -> None:
        if self.busy:
            return
        if self.photo is None:
            QMessageBox.information(self, "FaceStudio 2.0", "Upload a portrait first.")
            return
        if self.pipeline is None:
            self.choose_index()
            return

        self.busy = True
        self.generate_button.setEnabled(False)
        self.upload_button.setEnabled(False)
        self.progress.setValue(0)
        self.progress.setFormat("Starting…")
        self.footer_icon.setText("◉")
        self.footer_text.setText("Generation in progress. Real intermediate textures will appear below.")
        self._reset_stages()
        output = self.output_dir / f"{self.photo.stem}-facestudio2.png"

        try:
            result = self.pipeline.run(self.photo, output, self._on_progress)
            self._set_preview(self.texture_preview, result.generation.output, 680, 430)
            self.status.setText(
                f"Complete — donor {result.donor.name} ({result.donor.score:.2f}%). "
                f"Saved to {result.generation.output}"
            )
            self.footer_icon.setText("✓")
            self.footer_text.setText("Generation complete. Compare the source and UV, then test the PNG in game.")
        except Exception as exc:
            details = "".join(traceback.format_exception_only(type(exc), exc)).strip()
            self.status.setText(f"Generation failed: {details}")
            QMessageBox.critical(self, "FaceStudio generation failed", details)
        finally:
            self.busy = False
            self.generate_button.setEnabled(True)
            self.upload_button.setEnabled(True)

    def _on_progress(self, percent: int, message: str, preview: Path | None) -> None:
        self.progress.setValue(percent)
        self.progress.setFormat(f"{percent}%")
        self.status.setText(message)
        self._activate_stage(percent)
        if preview and Path(preview).is_file():
            self._set_preview(self.texture_preview, Path(preview), 680, 430)
            slot = self._thumbnail_slot(percent)
            if slot is not None:
                self._set_preview(self.preview_cards[slot][0], Path(preview), 150, 92)
        QApplication.processEvents()

    def _activate_stage(self, percent: int) -> None:
        for index, (_, threshold) in enumerate(self.STAGES):
            if percent >= threshold:
                self.stage_dots[index].setText("✓")
                self.stage_dots[index].setObjectName("StageDone")
                self.stage_dots[index].style().unpolish(self.stage_dots[index])
                self.stage_dots[index].style().polish(self.stage_dots[index])

    @staticmethod
    def _thumbnail_slot(percent: int) -> int | None:
        if percent <= 8: return 0
        if percent <= 25: return 1
        if percent <= 48: return 2
        if percent <= 68: return 3
        if percent <= 85: return 4
        if percent < 100: return 5
        return 6

    def _reset_stages(self) -> None:
        for dot in self.stage_dots:
            dot.setText("○")
            dot.setObjectName("StageIdle")
            dot.style().unpolish(dot)
            dot.style().polish(dot)
        for image, _ in self.preview_cards:
            image.clear()
            image.setText("—")

    def open_output_folder(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.output_dir)))

    @staticmethod
    def _set_preview(label: QLabel, path: Path, width: int, height: int) -> None:
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            label.setText(f"Could not preview\n{path}")
            return
        label.setPixmap(pixmap.scaled(width, height, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    @staticmethod
    def _stylesheet() -> str:
        return """
        QMainWindow, QWidget { background: #090e14; color: #eef4fb; font-family: 'Segoe UI'; font-size: 13px; }
        QFrame#Sidebar { background: #070c12; border-right: 1px solid #23303d; }
        QLabel#Brand { font-size: 27px; font-weight: 800; padding: 6px 0; }
        QLabel#PageTitle { font-size: 31px; font-weight: 800; }
        QLabel#AccentText { color: #3b94ff; font-weight: 700; }
        QLabel#Muted { color: #9dadbd; }
        QLabel#Status { color: #d7e6f5; padding: 2px 0; }
        QLabel#SectionTitle { font-size: 11px; font-weight: 800; color: #dbe9f7; }
        QLabel#MiniCard, QFrame#Card, QFrame#Timeline { background: #101720; border: 1px solid #253342; border-radius: 9px; }
        QLabel#MiniCard { padding: 10px; color: #cbd8e5; }
        QLabel#Preview { background: #0b1118; border: 1px solid #2c3d4d; border-radius: 7px; }
        QLabel#Thumb { background: #0b1118; border: 1px solid #2d4051; border-radius: 6px; }
        QLabel#Badge { background: #16884a; color: white; border-radius: 8px; padding: 2px 8px; font-size: 10px; font-weight: 800; }
        QLabel#StageIdle, QLabel#TopStageIdle { color: #526273; }
        QLabel#StageDone { color: #35d36f; font-weight: 800; }
        QLabel#StageText, QLabel#TopStageText { color: #d9e5f0; font-size: 11px; }
        QLabel#ReadyDot { color: #35d36f; font-size: 22px; }
        QPushButton { background: #182230; border: 1px solid #334255; border-radius: 7px; padding: 10px 12px; text-align: left; }
        QPushButton:hover { background: #213044; }
        QPushButton#Primary { background: #1478ed; border-color: #2b91ff; font-weight: 800; font-size: 14px; }
        QPushButton#Primary:hover { background: #2588f4; }
        QProgressBar { background: #17202b; border: none; border-radius: 4px; min-height: 8px; text-align: right; color: #eaf4ff; }
        QProgressBar::chunk { background: #2588f4; border-radius: 4px; }
        QScrollArea { border: none; }
        """

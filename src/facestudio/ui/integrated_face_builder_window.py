from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFileDialog, QFormLayout, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMainWindow, QMessageBox, QProgressBar,
    QPushButton, QSpinBox, QStackedWidget, QVBoxLayout, QWidget,
)

from facestudio.match_engine_research.builder_workspace import BuilderWorkspace, STAGES
from facestudio.match_engine_research.integrated_face_builder import (
    IntegratedBuildInputs, IntegratedFaceBuilderService,
)
from facestudio.ui.theme import DARK_STYLESHEET, LIGHT_STYLESHEET
from facestudio.utils.config import AppConfig

LABELS = {
    "home": "Home", "project": "Project", "source_photo": "Source Photo",
    "landmarks": "Landmark Editor", "geometry": "Geometry Analysis",
    "donor_search": "Donor Search", "donor_review": "Donor Review",
    "uv_calibration": "UV Calibration", "reconstruction": "Texture Reconstruction",
    "refinement": "Texture Refinement", "validation": "Validation",
    "preview": "Build Preview", "export": "Export", "settings": "Settings",
}
STATUS_SYMBOL = {
    "complete": "✓", "needs-review": "!", "running": "↻",
    "blocked": "×", "not-started": "○",
}


class IntegratedFaceBuilderWindow(QMainWindow):
    """Complete staged workspace around the implemented FaceStudio texture pipeline."""

    def __init__(self, config: AppConfig, config_path: Path) -> None:
        super().__init__()
        self.config = config
        self.config_path = config_path
        self.service = IntegratedFaceBuilderService()
        self.workspace_state = BuilderWorkspace()
        self.workspace_file: Path | None = None
        self.pages: dict[str, QWidget] = {}
        self.nav_items: dict[str, QListWidgetItem] = {}
        self.preview_labels: dict[str, QLabel] = {}
        self.path_labels: dict[str, QLabel] = {}
        self.setWindowTitle("FM FaceStudio — Alpha 8.1.0 — Complete Builder Workspace")
        self.resize(1540, 930)
        self.setMinimumSize(1120, 720)
        self.setStyleSheet(LIGHT_STYLESHEET if config.theme == "light" else DARK_STYLESHEET)
        self._build_ui()
        self._refresh_all()

    def _build_ui(self) -> None:
        root = QWidget(); self.setCentralWidget(root)
        outer = QHBoxLayout(root); outer.setContentsMargins(0, 0, 0, 0); outer.setSpacing(0)

        sidebar = QFrame(); sidebar.setObjectName("Sidebar"); sidebar.setFixedWidth(255)
        side = QVBoxLayout(sidebar); side.setContentsMargins(16, 22, 16, 18)
        brand = QLabel("FM FaceStudio"); brand.setObjectName("Brand"); side.addWidget(brand)
        version = QLabel("ALPHA 8.1.0\nCOMPLETE BUILDER WORKSPACE"); version.setObjectName("Muted"); side.addWidget(version)
        side.addSpacing(12)
        self.progress = QProgressBar(); self.progress.setRange(0, 100); side.addWidget(self.progress)
        self.progress_text = QLabel("0% complete"); self.progress_text.setObjectName("Muted"); side.addWidget(self.progress_text)
        side.addSpacing(10)
        self.nav = QListWidget(); self.nav.setFrameShape(QFrame.Shape.NoFrame)
        self.nav.currentRowChanged.connect(self._navigate)
        for name in STAGES:
            item = QListWidgetItem(); self.nav.addItem(item); self.nav_items[name] = item
        side.addWidget(self.nav, 1)
        self.build_button = QPushButton("✦  Build Face")
        self.build_button.setMinimumHeight(42); self.build_button.clicked.connect(self.build)
        side.addWidget(self.build_button)
        self.save_button = QPushButton("Save Workspace")
        self.save_button.clicked.connect(self.save_workspace); side.addWidget(self.save_button)
        boundary = QLabel("Texture workflow for an existing reviewed donor head. No .skin decoding, mesh generation or automatic FM file replacement.")
        boundary.setWordWrap(True); boundary.setObjectName("Muted"); side.addWidget(boundary)
        outer.addWidget(sidebar)

        self.stack = QStackedWidget(); outer.addWidget(self.stack, 1)
        self._add_page("home", self._home_page())
        self._add_page("project", self._project_page())
        self._add_page("source_photo", self._file_page("Source Photo", "Choose the clear front-facing photograph used by the reviewed landmark record.", "source_photo", "Images (*.png *.jpg *.jpeg *.webp *.bmp)", image=True))
        self._add_page("landmarks", self._file_page("Landmark Editor", "Select the corrected facestudio-landmarks-v1 record. Manual drag editing remains available in the dedicated research editor.", "portrait_record", "FaceStudio JSON (*.json)", image=True, image_field="source_path"))
        self._add_page("geometry", self._file_page("Geometry Analysis", "Select a reviewed facestudio-fm-head-geometry-v1 dataset containing measured face proportions.", "geometry_dataset", "FaceStudio JSON (*.json)"))
        self._add_page("donor_search", self._donor_page())
        self._add_page("donor_review", self._info_page("Donor Review", "Review the selected numeric donor ID and its manifest before continuing. Locking a donor prevents later stages from silently switching identity.", ("Confirm the geometry match", "Inspect available front and side renders", "Keep the donor ID locked throughout UV calibration and export")))
        self._add_page("uv_calibration", self._file_page("UV Calibration", "Select the completed facestudio-donor-uv-calibration-v1 record with all twelve reviewed anchors.", "uv_record", "FaceStudio JSON (*.json)", image=True, image_field="texture_path"))
        self._add_page("reconstruction", self._pipeline_page("Texture Reconstruction", "Triangulated barycentric transfer of the corrected portrait into the reviewed donor UV anchors.", "reconstruction_manifest"))
        self._add_page("refinement", self._refinement_page())
        self._add_page("validation", self._pipeline_page("Validation", "Check dimensions, alpha consistency, regional coverage, peripheral preservation and advisory readiness.", "validation_report"))
        self._add_page("preview", self._preview_page())
        self._add_page("export", self._export_page())
        self._add_page("settings", self._settings_page())
        self.nav.setCurrentRow(0)

    def _add_page(self, name: str, page: QWidget) -> None:
        self.pages[name] = page; self.stack.addWidget(page)

    @staticmethod
    def _page_shell(title: str, subtitle: str) -> tuple[QWidget, QVBoxLayout]:
        page = QWidget(); layout = QVBoxLayout(page); layout.setContentsMargins(28, 24, 28, 24); layout.setSpacing(15)
        heading = QLabel(title); heading.setStyleSheet("font-size: 29px; font-weight: 700;")
        description = QLabel(subtitle); description.setWordWrap(True); description.setObjectName("Muted")
        layout.addWidget(heading); layout.addWidget(description)
        return page, layout

    def _home_page(self) -> QWidget:
        page, layout = self._page_shell("Build One Reviewed FM Face", "Move through every stage from source photograph to a reversible controlled-test package.")
        card = QFrame(); card.setObjectName("Card"); box = QVBoxLayout(card)
        self.home_status = QLabel(); self.home_status.setWordWrap(True); self.home_status.setStyleSheet("font-size: 17px;")
        box.addWidget(self.home_status)
        open_button = QPushButton("Open Workspace"); open_button.clicked.connect(self.open_workspace)
        new_button = QPushButton("New Workspace"); new_button.clicked.connect(self.new_workspace)
        row = QHBoxLayout(); row.addWidget(open_button); row.addWidget(new_button); row.addStretch(); box.addLayout(row)
        layout.addWidget(card); layout.addStretch()
        return page

    def _project_page(self) -> QWidget:
        page, layout = self._page_shell("Project", "Name the build and choose the folder where its project state and generated artefacts are stored.")
        card = QFrame(); card.setObjectName("Card"); form = QFormLayout(card)
        self.project_name = QLineEdit(); self.project_name.textChanged.connect(self._project_name_changed)
        self.project_dir = QLabel("No workspace folder selected"); self.project_dir.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        choose = QPushButton("Choose Project Folder"); choose.clicked.connect(self.choose_project_directory)
        form.addRow("Project name", self.project_name); form.addRow("Workspace", self.project_dir); form.addRow("", choose)
        layout.addWidget(card); layout.addStretch(); return page

    def _file_page(self, title: str, subtitle: str, attribute: str, file_filter: str, image: bool = False, image_field: str | None = None) -> QWidget:
        page, layout = self._page_shell(title, subtitle)
        card = QFrame(); card.setObjectName("Card"); box = QVBoxLayout(card)
        path = QLabel("Nothing selected"); path.setWordWrap(True); path.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.path_labels[attribute] = path; box.addWidget(path)
        choose = QPushButton(f"Choose {title}")
        choose.clicked.connect(lambda: self._choose_file(attribute, title, file_filter, image_field)); box.addWidget(choose)
        if image:
            preview = QLabel("Awaiting input"); preview.setAlignment(Qt.AlignmentFlag.AlignCenter); preview.setMinimumHeight(430)
            preview.setStyleSheet("border: 1px solid #34404c; border-radius: 6px;")
            self.preview_labels[attribute] = preview; box.addWidget(preview, 1)
        layout.addWidget(card, 1); return page

    def _donor_page(self) -> QWidget:
        page, layout = self._page_shell("Donor Search", "Record the reviewed numeric donor and the donor-selection manifest produced by geometry matching.")
        card = QFrame(); card.setObjectName("Card"); form = QFormLayout(card)
        self.donor_id = QLineEdit(); self.donor_id.setPlaceholderText("Numeric player ID")
        self.donor_id.textChanged.connect(self._donor_changed)
        self.donor_manifest_label = QLabel("No donor manifest selected"); self.path_labels["donor_manifest"] = self.donor_manifest_label
        choose = QPushButton("Choose Donor Manifest"); choose.clicked.connect(lambda: self._choose_file("donor_manifest", "Donor manifest", "FaceStudio JSON (*.json)"))
        form.addRow("Donor player ID", self.donor_id); form.addRow("Manifest", self.donor_manifest_label); form.addRow("", choose)
        layout.addWidget(card); layout.addStretch(); return page

    def _pipeline_page(self, title: str, subtitle: str, attribute: str) -> QWidget:
        page, layout = self._page_shell(title, subtitle)
        card = QFrame(); card.setObjectName("Card"); box = QVBoxLayout(card)
        path = QLabel("Not generated yet"); path.setWordWrap(True); path.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.path_labels[attribute] = path; box.addWidget(path)
        run = QPushButton("Run Complete Build Pipeline"); run.clicked.connect(self.build); box.addWidget(run)
        layout.addWidget(card); layout.addStretch(); return page

    def _refinement_page(self) -> QWidget:
        page, layout = self._page_shell("Texture Refinement", "Configure the implemented seam feathering, donor colour matching and neighbour smoothing settings.")
        card = QFrame(); card.setObjectName("Card"); form = QFormLayout(card)
        self.feather = QSpinBox(); self.feather.setRange(0, 20); self.feather.setValue(6)
        self.colour = QSpinBox(); self.colour.setRange(0, 100); self.colour.setValue(65); self.colour.setSuffix("%")
        self.blend = QSpinBox(); self.blend.setRange(0, 100); self.blend.setValue(35); self.blend.setSuffix("%")
        form.addRow("Edge feather", self.feather); form.addRow("Colour matching", self.colour); form.addRow("Neighbour blend", self.blend)
        run = QPushButton("Run Complete Build Pipeline"); run.clicked.connect(self.build); form.addRow("", run)
        self.path_labels["refinement_manifest"] = QLabel("Not generated yet"); form.addRow("Result", self.path_labels["refinement_manifest"])
        layout.addWidget(card); layout.addStretch(); return page

    def _preview_page(self) -> QWidget:
        page, layout = self._page_shell("Build Preview", "Compare the reviewed source, donor UV texture and final refined texture.")
        row = QHBoxLayout()
        for key, title in (("source_photo", "Source"), ("uv_record", "Donor UV"), ("result", "Refined Result")):
            card = QFrame(); card.setObjectName("Card"); box = QVBoxLayout(card); box.addWidget(QLabel(title))
            preview = QLabel("Awaiting input"); preview.setAlignment(Qt.AlignmentFlag.AlignCenter); preview.setMinimumHeight(500)
            preview.setStyleSheet("border: 1px solid #34404c; border-radius: 6px;")
            self.preview_labels[f"preview_{key}"] = preview; box.addWidget(preview, 1); row.addWidget(card, 1)
        layout.addLayout(row, 1); return page

    def _export_page(self) -> QWidget:
        page, layout = self._page_shell("Export", "Create the validated PNG, reports, heatmap, build manifest and reversible controlled-test package.")
        card = QFrame(); card.setObjectName("Card"); box = QVBoxLayout(card)
        self.export_status = QLabel("No completed build available"); self.export_status.setWordWrap(True); box.addWidget(self.export_status)
        build = QPushButton("Build and Export"); build.clicked.connect(self.build); box.addWidget(build)
        layout.addWidget(card); layout.addStretch(); return page

    def _settings_page(self) -> QWidget:
        page, layout = self._page_shell("Settings", "Workspace-level controls. Application theme continues to use the existing FaceStudio configuration.")
        card = QFrame(); card.setObjectName("Card"); form = QFormLayout(card)
        theme = QLabel(self.config.theme.title()); form.addRow("Theme", theme)
        disclaimer = QLabel("Automatic FM installation remains disabled until the replacement workflow is proven safe.")
        disclaimer.setWordWrap(True); form.addRow("Safety", disclaimer)
        layout.addWidget(card); layout.addStretch(); return page

    def _info_page(self, title: str, subtitle: str, lines: tuple[str, ...]) -> QWidget:
        page, layout = self._page_shell(title, subtitle)
        card = QFrame(); card.setObjectName("Card"); box = QVBoxLayout(card)
        for line in lines: box.addWidget(QLabel(f"• {line}"))
        layout.addWidget(card); layout.addStretch(); return page

    def _navigate(self, row: int) -> None:
        if row >= 0: self.stack.setCurrentIndex(row)

    def _project_name_changed(self, value: str) -> None:
        self.workspace_state.project_name = value.strip() or "Untitled Face"; self._refresh_all()

    def _donor_changed(self, value: str) -> None:
        self.workspace_state.donor_player_id = value.strip(); self._refresh_all()

    def choose_project_directory(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Choose FaceStudio workspace")
        if not folder: return
        self.workspace_state.workspace_directory = folder
        self.workspace_file = Path(folder) / "facestudio-workspace.json"
        self._refresh_all()

    def _choose_file(self, attribute: str, title: str, file_filter: str, image_field: str | None = None) -> None:
        filename, _ = QFileDialog.getOpenFileName(self, title, "", file_filter)
        if not filename: return
        setattr(self.workspace_state, attribute, filename)
        if attribute == "portrait_record" and not self.workspace_state.source_photo:
            self.workspace_state.source_photo = self._json_path(Path(filename), "source_path")
        if attribute == "uv_record" and not self.workspace_state.donor_player_id:
            try:
                payload = json.loads(Path(filename).read_text(encoding="utf-8")); self.workspace_state.donor_player_id = str(payload.get("player_id", ""))
                self.donor_id.setText(self.workspace_state.donor_player_id)
            except (OSError, json.JSONDecodeError):
                pass
        self._refresh_all()
        image_path = self._json_path(Path(filename), image_field) if image_field else filename
        if attribute in self.preview_labels: self._set_preview(self.preview_labels[attribute], image_path)

    @staticmethod
    def _json_path(record: Path, field: str | None) -> str:
        if not field: return str(record)
        try: return str(json.loads(record.read_text(encoding="utf-8")).get(field, ""))
        except (OSError, json.JSONDecodeError): return ""

    @staticmethod
    def _set_preview(label: QLabel, path: str) -> None:
        pixmap = QPixmap(path)
        if pixmap.isNull(): label.setText("Preview unavailable"); return
        label.setPixmap(pixmap.scaled(470, 520, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def new_workspace(self) -> None:
        self.workspace_state = BuilderWorkspace(); self.workspace_file = None; self._refresh_all(); self.nav.setCurrentRow(1)

    def open_workspace(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(self, "Open FaceStudio workspace", "", "FaceStudio Workspace (*.json)")
        if not filename: return
        try: self.workspace_state = BuilderWorkspace.load(Path(filename)); self.workspace_file = Path(filename)
        except ValueError as exc: QMessageBox.critical(self, "Open workspace failed", str(exc)); return
        self._refresh_all()

    def save_workspace(self) -> None:
        if not self.workspace_file:
            if not self.workspace_state.workspace_directory:
                self.choose_project_directory()
            if not self.workspace_state.workspace_directory: return
            self.workspace_file = Path(self.workspace_state.workspace_directory) / "facestudio-workspace.json"
        try: self.workspace_state.save(self.workspace_file)
        except OSError as exc: QMessageBox.critical(self, "Save workspace failed", str(exc)); return
        QMessageBox.information(self, "Workspace saved", str(self.workspace_file))

    def build(self) -> None:
        portrait = Path(self.workspace_state.portrait_record) if self.workspace_state.portrait_record else None
        uv = Path(self.workspace_state.uv_record) if self.workspace_state.uv_record else None
        output = Path(self.workspace_state.workspace_directory) if self.workspace_state.workspace_directory else None
        if not portrait or not uv or not output:
            QMessageBox.information(self, "Build prerequisites", "Complete the Project, Landmark Editor and UV Calibration pages first.")
            return
        self.build_button.setEnabled(False); self.workspace_state.mark_running_from("reconstruction"); self._refresh_all()
        try:
            result = self.service.build(IntegratedBuildInputs(portrait, uv, output))
            manifest = output / "facestudio-integrated-build.json"
            self.workspace_state.reconstruction_manifest = str(result.reconstruction_manifest)
            self.workspace_state.refinement_manifest = str(result.refinement_manifest)
            report = output / "validation.validation.json"
            self.workspace_state.record_integrated_build(manifest, report if report.exists() else None)
            self.workspace_state.save(output / "facestudio-workspace.json")
            refined = result.validation_result.refined_texture
            self._set_preview(self.preview_labels["preview_result"], refined)
            self.export_status.setText(f"Validation score: {result.validation_result.quality_score}%\nIntegrated manifest: {manifest}\nPackage: {result.package_directory or 'not created; review validation report'}")
            QMessageBox.information(self, "Build complete", self.export_status.text())
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Build failed", str(exc))
        finally:
            self.build_button.setEnabled(True); self._refresh_all()

    def _refresh_all(self) -> None:
        self.workspace_state.refresh()
        self.progress.setValue(self.workspace_state.progress); self.progress_text.setText(f"{self.workspace_state.progress}% complete")
        self.home_status.setText(f"Project: {self.workspace_state.project_name}\nProgress: {self.workspace_state.progress}%\nNext action: {self._next_action()}")
        self.project_name.blockSignals(True); self.project_name.setText(self.workspace_state.project_name); self.project_name.blockSignals(False)
        self.project_dir.setText(self.workspace_state.workspace_directory or "No workspace folder selected")
        self.donor_id.blockSignals(True); self.donor_id.setText(self.workspace_state.donor_player_id); self.donor_id.blockSignals(False)
        for attribute, label in self.path_labels.items():
            value = getattr(self.workspace_state, attribute, "")
            label.setText(value or "Nothing selected / not generated yet")
        for index, name in enumerate(STAGES):
            state = self.workspace_state.stages[name]
            self.nav_items[name].setText(f"{STATUS_SYMBOL[state.status]}  {LABELS[name]}")
            self.nav_items[name].setToolTip(state.detail)
        if self.workspace_state.source_photo:
            self._set_preview(self.preview_labels.get("source_photo", QLabel()), self.workspace_state.source_photo)
            self._set_preview(self.preview_labels["preview_source_photo"], self.workspace_state.source_photo)
        if self.workspace_state.uv_record:
            texture = self._json_path(Path(self.workspace_state.uv_record), "texture_path")
            self._set_preview(self.preview_labels.get("uv_record", QLabel()), texture)
            self._set_preview(self.preview_labels["preview_uv_record"], texture)
        self.export_status.setText(self.workspace_state.integrated_manifest or "No completed build available")

    def _next_action(self) -> str:
        for name in STAGES:
            state = self.workspace_state.stages[name]
            if state.status in {"needs-review", "blocked", "not-started"} and name not in {"settings"}:
                return f"{LABELS[name]} — {state.detail}"
        return "Build is complete"

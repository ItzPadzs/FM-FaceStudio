from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from facestudio.mesh.inspection import inspect_binary
from facestudio.mesh.obj_loader import ObjFormatError, load_obj
from facestudio.ui.widgets.activity_banner import ActivityBanner
from facestudio.ui.widgets.mesh_viewport import MeshViewport
from facestudio.ui.widgets.page_header import PageHeader


class MeshViewerPage(QWidget):
    status_message = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.current_path: Path | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(16)

        self.open_button = QPushButton("Open file…")
        self.open_button.setObjectName("Primary")
        self.open_button.clicked.connect(self.open_dialog)
        self.reset_button = QPushButton("Reset camera")
        self.reset_button.setObjectName("Secondary")
        self.reset_button.clicked.connect(self._reset_view)

        layout.addWidget(
            PageHeader(
                "Read-only geometry research",
                "Mesh Explorer",
                "Render standard Wavefront OBJ geometry and inspect unknown files "
                "without modifying or claiming to decode proprietary Football Manager assets.",
                [self.reset_button, self.open_button],
            )
        )

        self.activity = ActivityBanner(
            "Open a Wavefront OBJ for rendering or another file for safe header inspection."
        )
        layout.addWidget(self.activity)

        toolbar = QGroupBox("Viewport controls")
        toolbar.setObjectName("WorkspaceCard")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(16, 20, 16, 16)

        front_button = QPushButton("Front")
        side_button = QPushButton("Side")
        top_button = QPushButton("Top")
        perspective_button = QPushButton("Perspective")
        zoom_out_button = QPushButton("−")
        zoom_in_button = QPushButton("+")
        front_button.clicked.connect(lambda: self.viewport.set_view(0.0, 0.0))
        side_button.clicked.connect(lambda: self.viewport.set_view(90.0, 0.0))
        top_button.clicked.connect(lambda: self.viewport.set_view(0.0, -89.0))
        perspective_button.clicked.connect(lambda: self.viewport.set_view(-25.0, 15.0))
        zoom_out_button.clicked.connect(self.viewport_zoom_out)
        zoom_in_button.clicked.connect(self.viewport_zoom_in)

        self.grid_toggle = QCheckBox("Grid")
        self.grid_toggle.setChecked(True)
        self.grid_toggle.toggled.connect(self._set_grid_visible)
        self.vertices_toggle = QCheckBox("Vertices")
        self.vertices_toggle.setChecked(True)
        self.vertices_toggle.toggled.connect(self._set_vertices_visible)

        for button in (front_button, side_button, top_button, perspective_button):
            toolbar_layout.addWidget(button)
        toolbar_layout.addSpacing(8)
        toolbar_layout.addWidget(zoom_out_button)
        toolbar_layout.addWidget(zoom_in_button)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(self.grid_toggle)
        toolbar_layout.addWidget(self.vertices_toggle)
        layout.addWidget(toolbar)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        viewport_box = QGroupBox("Geometry viewport")
        viewport_box.setObjectName("WorkspaceCard")
        viewport_layout = QVBoxLayout(viewport_box)
        viewport_layout.setContentsMargins(12, 18, 12, 12)
        self.viewport = MeshViewport()
        viewport_layout.addWidget(self.viewport)
        helper = QLabel(
            "Drag to rotate · Shift + drag to pan · Mouse wheel to zoom"
        )
        helper.setObjectName("Muted")
        helper.setAlignment(Qt.AlignmentFlag.AlignCenter)
        viewport_layout.addWidget(helper)
        splitter.addWidget(viewport_box)

        details_widget = QWidget()
        details_widget.setMinimumWidth(340)
        details_layout = QVBoxLayout(details_widget)
        details_layout.setContentsMargins(8, 0, 0, 0)
        details_layout.setSpacing(14)

        details_box = QGroupBox("Asset details")
        details_box.setObjectName("WorkspaceCard")
        form = QFormLayout(details_box)
        form.setContentsMargins(16, 20, 16, 16)
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(10)
        self.file_label = QLabel("No file open")
        self.file_label.setWordWrap(True)
        self.format_label = QLabel("—")
        self.vertices_label = QLabel("—")
        self.edges_label = QLabel("—")
        self.faces_label = QLabel("—")
        self.bounds_label = QLabel("—")
        self.bounds_label.setWordWrap(True)
        for label in (
            self.format_label,
            self.vertices_label,
            self.edges_label,
            self.faces_label,
        ):
            label.setObjectName("MetricValue")
        form.addRow("File", self.file_label)
        form.addRow("Mode", self.format_label)
        form.addRow("Vertices", self.vertices_label)
        form.addRow("Edges", self.edges_label)
        form.addRow("Faces", self.faces_label)
        form.addRow("Bounds", self.bounds_label)
        details_layout.addWidget(details_box)

        inspection_box = QGroupBox("Read-only inspection")
        inspection_box.setObjectName("WorkspaceCard")
        inspection_layout = QVBoxLayout(inspection_box)
        inspection_layout.setContentsMargins(12, 18, 12, 12)
        self.inspection = QPlainTextEdit()
        self.inspection.setObjectName("AnalysisDetails")
        self.inspection.setReadOnly(True)
        self.inspection.setPlaceholderText(
            "Binary header or OBJ information will appear here."
        )
        inspection_layout.addWidget(self.inspection)
        details_layout.addWidget(inspection_box, 1)

        splitter.addWidget(details_widget)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([920, 360])
        layout.addWidget(splitter, 1)

    def viewport_zoom_in(self) -> None:
        self.viewport.zoom_in()

    def viewport_zoom_out(self) -> None:
        self.viewport.zoom_out()

    def _set_grid_visible(self, visible: bool) -> None:
        self.viewport.set_grid_visible(visible)

    def _set_vertices_visible(self, visible: bool) -> None:
        self.viewport.set_vertices_visible(visible)

    def open_dialog(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Open mesh or asset",
            "",
            "Supported meshes (*.obj);;All files (*.*)",
        )
        if filename:
            self.open_path(Path(filename))

    def open_path(self, path: Path) -> None:
        self.current_path = path
        self.file_label.setText(str(path))
        self.activity.set_state(f"Opening {path.name}…", True)
        if path.suffix.lower() == ".obj":
            self._open_obj(path)
        else:
            self._inspect_unknown(path)

    def _open_obj(self, path: Path) -> None:
        try:
            mesh = load_obj(path)
        except (OSError, ObjFormatError) as exc:
            self.viewport.set_mesh(None)
            self.format_label.setText("OBJ load error")
            self.inspection.setPlainText(str(exc))
            self.activity.set_state(f"Unable to load OBJ: {exc}")
            self.status_message.emit(f"Unable to load OBJ: {exc}")
            return

        self.viewport.set_mesh(mesh)
        minimum, maximum = mesh.bounds()
        self.format_label.setText("Wavefront OBJ — rendered")
        self.vertices_label.setText(f"{mesh.vertex_count:,}")
        self.edges_label.setText(f"{mesh.edge_count:,}")
        self.faces_label.setText(f"{mesh.face_count:,}")
        self.bounds_label.setText(
            f"Min ({minimum.x:.3f}, {minimum.y:.3f}, {minimum.z:.3f})\n"
            f"Max ({maximum.x:.3f}, {maximum.y:.3f}, {maximum.z:.3f})"
        )
        self.inspection.setPlainText(
            "OBJ loaded successfully.\n\n"
            "Rendering mode: standard Wavefront OBJ wireframe.\n"
            "Camera presets and grid controls affect display only.\n\n"
            "No game files were modified."
        )
        message = (
            f"Rendered {path.name}: {mesh.vertex_count:,} vertices, "
            f"{mesh.edge_count:,} edges and {mesh.face_count:,} faces."
        )
        self.activity.set_state(message)
        self.status_message.emit(message)

    def _inspect_unknown(self, path: Path) -> None:
        self.viewport.set_mesh(None)
        self.vertices_label.setText("—")
        self.edges_label.setText("—")
        self.faces_label.setText("—")
        self.bounds_label.setText("—")

        try:
            report = inspect_binary(path)
        except OSError as exc:
            self.format_label.setText("Read error")
            self.inspection.setPlainText(str(exc))
            self.activity.set_state(f"Unable to inspect file: {exc}")
            self.status_message.emit(f"Unable to inspect file: {exc}")
            return

        suffix = path.suffix.lower() or "(no extension)"
        self.format_label.setText(f"{suffix} — inspection only")
        self.inspection.setPlainText(
            f"Size: {report.size_bytes:,} bytes\n\n"
            "First bytes (hex):\n"
            f"{report.header_hex}\n\n"
            "Printable view:\n"
            f"{report.printable_header}\n\n"
            "This file has not been decoded or rendered. "
            "No assumptions are being made about its proprietary structure."
        )
        message = f"Opened {path.name} in safe inspection-only mode."
        self.activity.set_state(message)
        self.status_message.emit(message)

    def _reset_view(self) -> None:
        self.viewport.reset_view()
        self.activity.set_state("Camera reset to the default perspective view.")

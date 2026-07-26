from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
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
from facestudio.ui.widgets.mesh_viewport import MeshViewport


class MeshViewerPage(QWidget):
    status_message = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.current_path: Path | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(12)

        title_row = QHBoxLayout()
        title = QLabel("Mesh Explorer")
        title.setObjectName("PageTitle")
        title_row.addWidget(title)
        title_row.addStretch()

        open_button = QPushButton("Open file…")
        open_button.setObjectName("Primary")
        open_button.clicked.connect(self.open_dialog)
        reset_button = QPushButton("Reset view")
        reset_button.clicked.connect(self._reset_view)
        title_row.addWidget(open_button)
        title_row.addWidget(reset_button)
        layout.addLayout(title_row)

        notice = QLabel(
            "Sprint 4 renders standard Wavefront OBJ files. Unknown or proprietary "
            "files can be inspected safely, but are not decoded."
        )
        notice.setObjectName("Muted")
        notice.setWordWrap(True)
        layout.addWidget(notice)

        splitter = QSplitter()
        self.viewport = MeshViewport()
        splitter.addWidget(self.viewport)

        details_widget = QWidget()
        details_widget.setMinimumWidth(320)
        details_layout = QVBoxLayout(details_widget)
        details_layout.setContentsMargins(12, 0, 0, 0)

        details_box = QGroupBox("Asset details")
        form = QFormLayout(details_box)
        self.file_label = QLabel("No file open")
        self.file_label.setWordWrap(True)
        self.format_label = QLabel("—")
        self.vertices_label = QLabel("—")
        self.edges_label = QLabel("—")
        self.faces_label = QLabel("—")
        self.bounds_label = QLabel("—")
        self.bounds_label.setWordWrap(True)
        form.addRow("File", self.file_label)
        form.addRow("Mode", self.format_label)
        form.addRow("Vertices", self.vertices_label)
        form.addRow("Edges", self.edges_label)
        form.addRow("Faces", self.faces_label)
        form.addRow("Bounds", self.bounds_label)
        details_layout.addWidget(details_box)

        inspection_box = QGroupBox("Read-only inspection")
        inspection_layout = QVBoxLayout(inspection_box)
        self.inspection = QPlainTextEdit()
        self.inspection.setReadOnly(True)
        self.inspection.setPlaceholderText(
            "Binary header or OBJ information will appear here."
        )
        inspection_layout.addWidget(self.inspection)
        details_layout.addWidget(inspection_box, 1)

        splitter.addWidget(details_widget)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter, 1)

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
            "Controls:\n"
            "• Drag: rotate\n"
            "• Shift + drag: pan\n"
            "• Mouse wheel: zoom\n"
            "• Reset view: restore camera"
        )
        self.status_message.emit(
            f"Loaded OBJ with {mesh.vertex_count:,} vertices."
        )

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
        self.status_message.emit("Opened file in inspection-only mode.")

    def _reset_view(self) -> None:
        self.viewport.reset_view()

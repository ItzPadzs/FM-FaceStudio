from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QPainter, QPen
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from facestudio.hair.export import build_native_hair_package
from facestudio.hair.models import HairMatchResult, HairSelection
from facestudio.hair.service import HairMatchingService
from facestudio.hair.skin import HairMesh, read_fm26_hair_skin
from facestudio.ui.widgets.activity_banner import ActivityBanner
from facestudio.ui.widgets.page_header import PageHeader


class HairProjectionWidget(QWidget):
    """Fast orthographic silhouette preview for a native FM hair .skin."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.mesh: HairMesh | None = None
        self.setMinimumHeight(220)

    def set_skin(self, path: Path | None) -> None:
        try:
            self.mesh = read_fm26_hair_skin(path) if path else None
        except Exception:
            self.mesh = None
        self.update()

    @staticmethod
    def _normalise(points: list[tuple[float, float]], width: float, height: float) -> list[QPointF]:
        if not points:
            return []
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        x0, x1 = min(xs), max(xs)
        y0, y1 = min(ys), max(ys)
        dx = max(x1 - x0, 1e-9)
        dy = max(y1 - y0, 1e-9)
        scale = min((width - 18.0) / dx, (height - 28.0) / dy)
        ox = (width - dx * scale) * 0.5
        oy = (height - dy * scale) * 0.5
        return [QPointF(ox + (x - x0) * scale, height - (oy + (y - y0) * scale)) for x, y in points]

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.fillRect(self.rect(), self.palette().base())
        painter.setPen(QPen(self.palette().mid().color(), 1))
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))

        if self.mesh is None or not self.mesh.positions:
            painter.setPen(self.palette().text().color())
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Select a ranked hair to preview")
            return

        panels = [
            ("Front", [(x, y) for x, y, _z in self.mesh.positions]),
            ("Side", [(z, y) for _x, y, z in self.mesh.positions]),
            ("Top", [(x, z) for x, _y, z in self.mesh.positions]),
        ]
        panel_width = self.width() / 3.0
        point_pen = QPen(self.palette().text().color(), 1)
        label_pen = QPen(self.palette().mid().color(), 1)
        step = max(1, len(self.mesh.positions) // 5000)
        for index, (label, source) in enumerate(panels):
            left = index * panel_width
            painter.setPen(label_pen)
            painter.drawText(int(left + 8), 18, label)
            sampled = source[::step]
            normalised = self._normalise(sampled, panel_width, self.height())
            painter.setPen(point_pen)
            for point in normalised:
                painter.drawPoint(QPointF(left + point.x(), point.y()))
            if index:
                painter.setPen(label_pen)
                painter.drawLine(int(left), 0, int(left), self.height())


class HairCompareDialog(QDialog):
    def __init__(self, results: list[HairMatchResult], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Compare Hair Candidates")
        self.resize(1100, 640)
        layout = QGridLayout(self)
        for index, result in enumerate(results[:4]):
            box = QGroupBox(
                f"#{index + 1}  {result.candidate.display_name} — {result.percentage:.1f}%"
            )
            inner = QVBoxLayout(box)
            preview = HairProjectionWidget()
            preview.set_skin(result.candidate.contract.skin)
            inner.addWidget(preview)
            details = QLabel(
                f"UID {result.candidate.contract.uid}  •  "
                f"{result.candidate.descriptor.vertex_count:,}V / "
                f"{result.candidate.descriptor.triangle_count:,}T  •  "
                f"{'PROVEN' if result.candidate.proven else 'Untested'}"
            )
            details.setWordWrap(True)
            inner.addWidget(details)
            layout.addWidget(box, index // 2, index % 2)


class HairMatcherPage(QWidget):
    selection_changed = Signal(object)

    MODES = (
        "Automatic Best Match",
        "Choose Manually",
        "Use FM Native Player Hair",
        "No Custom Hair",
    )

    def __init__(self, state_root: Path) -> None:
        super().__init__()
        self.project: object | None = None
        self.directory: Path | None = None
        self.state_root = state_root
        self.service = HairMatchingService(
            cache_path=state_root / "hair-library-cache.json",
            proven_path=state_root / "hair-proven.json",
        )
        self.results: list[HairMatchResult] = []
        self.filtered_results: list[HairMatchResult] = []
        self.selected_result: HairMatchResult | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(16)

        self.rank_button = QPushButton("Rank Hair Library")
        self.rank_button.setObjectName("Primary")
        self.rank_button.clicked.connect(self._rank)
        self.compare_button = QPushButton("Compare Top 4")
        self.compare_button.clicked.connect(self._compare)
        self.compare_button.setEnabled(False)

        layout.addWidget(
            PageHeader(
                "Hair Matcher",
                "Automatic recommendation + manual donor selection",
                "Rank native FM26 hair against the source hairstyle, then keep the recommendation or override it manually. Native hair files are never normalised or rebuilt.",
                [self.rank_button, self.compare_button],
            )
        )

        self.activity = ActivityBanner(
            "Choose a source FM hair .skin (or feed a source descriptor from the converter) and the FM hair library."
        )
        layout.addWidget(self.activity)

        controls = QGroupBox("Hair selection")
        controls.setObjectName("WorkspaceCard")
        form = QFormLayout(controls)
        self.mode = QComboBox()
        self.mode.addItems(self.MODES)
        self.mode.currentTextChanged.connect(self._mode_changed)
        self.source_path = QLineEdit()
        self.library_path = QLineEdit()
        source_row = QWidget()
        source_layout = QHBoxLayout(source_row)
        source_layout.setContentsMargins(0, 0, 0, 0)
        source_layout.addWidget(self.source_path, 1)
        source_button = QPushButton("Browse…")
        source_button.clicked.connect(self._choose_source)
        source_layout.addWidget(source_button)
        library_row = QWidget()
        library_layout = QHBoxLayout(library_row)
        library_layout.setContentsMargins(0, 0, 0, 0)
        library_layout.addWidget(self.library_path, 1)
        library_button = QPushButton("Browse…")
        library_button.clicked.connect(self._choose_library)
        library_layout.addWidget(library_button)
        form.addRow("Mode", self.mode)
        form.addRow("Source hairstyle", source_row)
        form.addRow("FM hair library", library_row)
        layout.addWidget(controls)

        row = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Filter by player name, UID or donor path…")
        self.search.textChanged.connect(self._apply_filter)
        row.addWidget(self.search, 1)
        self.mark_proven = QPushButton("Mark Proven")
        self.mark_proven.clicked.connect(self._mark_proven)
        self.mark_proven.setEnabled(False)
        row.addWidget(self.mark_proven)
        self.export_button = QPushButton("Build Hair Test Package…")
        self.export_button.clicked.connect(self._export)
        self.export_button.setEnabled(False)
        row.addWidget(self.export_button)
        layout.addLayout(row)

        body = QHBoxLayout()
        results_box = QGroupBox("Ranked native FM hair")
        results_layout = QVBoxLayout(results_box)
        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels(
            ["Rank", "Donor", "UID", "Match", "Status", "Contract", "Vertices", "Triangles", "Notes"]
        )
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.itemSelectionChanged.connect(self._table_selection_changed)
        results_layout.addWidget(self.table)
        body.addWidget(results_box, 3)

        preview_box = QGroupBox("Selected hair preview")
        preview_layout = QVBoxLayout(preview_box)
        self.preview = HairProjectionWidget()
        preview_layout.addWidget(self.preview)
        self.selected_label = QLabel("No hair selected")
        self.selected_label.setWordWrap(True)
        preview_layout.addWidget(self.selected_label)
        body.addWidget(preview_box, 2)
        layout.addLayout(body, 1)

    def _choose_source(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(self, "Choose source FM hair skin", "", "FM hair (*.skin)")
        if filename:
            self.source_path.setText(filename)

    def _choose_library(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Choose FM26 hair library")
        if folder:
            self.library_path.setText(folder)

    def _rank(self) -> None:
        source = Path(self.source_path.text().strip())
        library = Path(self.library_path.text().strip())
        if not source.is_file():
            QMessageBox.warning(self, "Source hair required", "Choose a source hairstyle .skin first.")
            return
        if not library.is_dir():
            QMessageBox.warning(self, "Hair library required", "Choose the FM hair library folder first.")
            return
        self.activity.set_state("Indexing native hair and calculating silhouette matches…", True)
        try:
            self.results = self.service.rank_skin_against_library(source, library, limit=None)
        except Exception as exc:
            self.activity.set_state(f"Hair matching failed: {exc}", False)
            QMessageBox.critical(self, "Hair matching failed", str(exc))
            return
        self.activity.set_state(f"Hair ranking complete — {len(self.results):,} candidates scored.", False)

        if self.directory:
            self.service.write_report(
                self.directory / "hair-match-report.json",
                self.results,
                source=str(source),
                library_root=str(library),
            )
        self._apply_filter()
        self.compare_button.setEnabled(bool(self.results))
        if self.results and self.mode.currentText() == "Automatic Best Match":
            self.table.selectRow(0)
            self._choose_result(self.results[0])

    def _apply_filter(self) -> None:
        term = self.search.text().strip().lower()
        if term:
            self.filtered_results = [
                result for result in self.results
                if term in result.candidate.display_name.lower()
                or term in result.candidate.contract.uid.lower()
                or term in str(result.candidate.contract.skin).lower()
            ]
        else:
            self.filtered_results = list(self.results)
        self._render_table()

    def _render_table(self) -> None:
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(self.filtered_results))
        for row, result in enumerate(self.filtered_results):
            candidate = result.candidate
            descriptor = candidate.descriptor
            values = [
                str(self.results.index(result) + 1),
                candidate.display_name,
                candidate.contract.uid,
                f"{result.percentage:.1f}%",
                "PROVEN" if candidate.proven else "Untested",
                "Complete" if candidate.contract.complete else "Incomplete",
                f"{descriptor.vertex_count:,}",
                f"{descriptor.triangle_count:,}",
                candidate.notes or ("; ".join(result.warnings) if result.warnings else "—"),
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, result.candidate.candidate_id)
                self.table.setItem(row, column, item)
        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSortingEnabled(True)

    def _result_for_row(self, row: int) -> HairMatchResult | None:
        item = self.table.item(row, 0)
        candidate_id = item.data(Qt.ItemDataRole.UserRole) if item else None
        if not candidate_id:
            return None
        return next(
            (result for result in self.results if result.candidate.candidate_id == candidate_id),
            None,
        )

    def _table_selection_changed(self) -> None:
        rows = sorted({index.row() for index in self.table.selectionModel().selectedRows()})
        if not rows:
            return
        result = self._result_for_row(rows[0])
        if result is not None:
            self._choose_result(result)

    def _choose_result(self, result: HairMatchResult) -> None:
        self.selected_result = result
        candidate = result.candidate
        self.preview.set_skin(candidate.contract.skin)
        self.selected_label.setText(
            f"{candidate.display_name} · UID {candidate.contract.uid}\n"
            f"Match {result.percentage:.1f}% · {'PROVEN' if candidate.proven else 'Untested'} · "
            f"{candidate.descriptor.vertex_count:,} vertices / {candidate.descriptor.triangle_count:,} triangles\n"
            f"Native files: {candidate.contract.skin.name}, "
            f"{candidate.contract.diffuse.name if candidate.contract.diffuse else 'missing diffuse'}, "
            f"{', '.join(path.name for path in candidate.contract.normal_files) or 'no normal supplied'}"
        )
        self.mark_proven.setEnabled(True)
        self.mark_proven.setText("Unmark Proven" if candidate.proven else "Mark Proven")
        self.export_button.setEnabled(candidate.contract.complete)
        self._save_selection(result)

    def _save_selection(self, result: HairMatchResult | None) -> None:
        if not self.directory:
            return
        mode = self.mode.currentText()
        selection = HairSelection(
            mode=mode,
            candidate_id=result.candidate.candidate_id if result else None,
            source="automatic" if mode == "Automatic Best Match" else "manual",
            similarity=result.similarity if result else None,
        )
        self.service.save_selection(self.directory / "hair-selection.json", selection)
        self.selection_changed.emit(selection)

    def _mode_changed(self, mode: str) -> None:
        if mode == "Automatic Best Match" and self.results:
            self._choose_result(self.results[0])
        elif mode in {"Use FM Native Player Hair", "No Custom Hair"}:
            self.selected_result = None
            self.preview.set_skin(None)
            self.selected_label.setText(mode)
            self.export_button.setEnabled(False)
            self.mark_proven.setEnabled(False)
            self._save_selection(None)
        else:
            self._save_selection(self.selected_result)

    def _compare(self) -> None:
        rows = sorted({index.row() for index in self.table.selectionModel().selectedRows()})
        if rows:
            chosen = [result for row in rows[:4] if (result := self._result_for_row(row)) is not None]
        else:
            chosen = self.results[:4]
        if not chosen:
            return
        HairCompareDialog(chosen, self).exec()

    def _mark_proven(self) -> None:
        if not self.selected_result:
            return
        candidate = self.selected_result.candidate
        self.service.library.set_proven(candidate.candidate_id, not candidate.proven)
        # Re-rank to apply/remove the small proven confidence bonus and refresh state.
        self._rank()

    def _export(self) -> None:
        if not self.selected_result:
            return
        uid, accepted = QInputDialog.getText(self, "Target FM26 UID", "Target player UID:")
        if not accepted or not uid.strip():
            return
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save untouched native hair test package",
            f"{uid.strip()}-NativeHair-{self.selected_result.candidate.contract.uid}.zip",
            "ZIP package (*.zip)",
        )
        if not filename:
            return
        try:
            path = build_native_hair_package(self.selected_result.candidate, uid, Path(filename))
        except Exception as exc:
            QMessageBox.critical(self, "Hair export failed", str(exc))
            return
        QMessageBox.information(
            self,
            "Hair package built",
            f"Built untouched native donor hair package:\n{path}\n\nOnly filenames changed; donor asset bytes were verified after copying.",
        )

    def set_project(self, project: object | None, directory: Path | None) -> None:
        self.project = project
        self.directory = directory

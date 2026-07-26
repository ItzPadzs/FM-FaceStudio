from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import QThread
from PySide6.QtWidgets import QFrame, QPushButton, QVBoxLayout

from facestudio.batch.worker import BatchAnalysisWorker
from facestudio.library.store import FaceLibraryRecord
from facestudio.ui.library_window import LibraryMainWindow
from facestudio.ui.pages.batch_analysis import BatchAnalysisPage
from facestudio.utils.config import AppConfig


class BatchMainWindow(LibraryMainWindow):
    """Alpha 0.9 shell with persistent library and sequential batch analysis."""

    def __init__(self, config: AppConfig, config_path: Path) -> None:
        super().__init__(config, config_path)
        self.batch_thread: QThread | None = None
        self.batch_worker: BatchAnalysisWorker | None = None
        self.batch_succeeded = 0
        self.batch_failed = 0

        self.batch_analysis = BatchAnalysisPage()
        self.batch_analysis.start_requested.connect(self.start_batch_analysis)
        self.batch_analysis.cancel_requested.connect(self.cancel_batch_analysis)

        page_index = self.stack.count()
        self.stack.addWidget(self.batch_analysis)
        batch_button = QPushButton("Batch Analysis")
        batch_button.setObjectName("NavButton")
        batch_button.setCheckable(True)
        batch_button.clicked.connect(
            lambda checked=False, index=page_index: self.navigate(index)
        )
        self.nav_buttons.append(batch_button)

        sidebar = self.findChild(QFrame, "Sidebar")
        layout = sidebar.layout() if sidebar is not None else None
        if isinstance(layout, QVBoxLayout):
            layout.insertWidget(max(0, layout.count() - 3), batch_button)
        self.apply_theme(self.config.theme)

    def start_batch_analysis(self, sources: list[Path], output_path: str) -> None:
        if self.batch_thread is not None:
            return
        self.batch_succeeded = 0
        self.batch_failed = 0
        thread = QThread(self)
        worker = BatchAnalysisWorker([Path(path) for path in sources], Path(output_path))
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.progress.connect(self.batch_analysis.update_progress)
        worker.item_completed.connect(self._batch_item_completed)
        worker.item_failed.connect(self._batch_item_failed)
        worker.completed.connect(self._batch_completed)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._clear_batch_worker)
        self.batch_thread = thread
        self.batch_worker = worker
        self.batch_analysis.set_running(True)
        thread.start()

    def cancel_batch_analysis(self) -> None:
        if self.batch_worker is not None:
            self.batch_worker.cancel()
            self.batch_analysis.activity.set_state(
                "Cancellation requested. The current photograph will finish safely."
            )

    def _batch_item_completed(self, result: dict) -> None:
        self.batch_succeeded += 1
        self.batch_analysis.mark_completed(result)
        records = self.face_library_store.load()
        records.insert(0, FaceLibraryRecord(
            id=str(uuid4()),
            name=str(result.get("name", "Untitled face")),
            project_path="",
            source_photo=str(result.get("source_path", "")),
            preview_path=str(result.get("preview_path", "")),
            analysis_path=str(result.get("analysis_path", "")),
            face_shape=str(result.get("face_shape", "undetermined")),
            confidence=float(result.get("confidence", 0.0)),
            measurements={
                str(key): float(value)
                for key, value in dict(result.get("measurements", {})).items()
            },
            tags=["batch-analysis"],
            collection="Batch Imports",
            notes="Imported through Batch Analysis.",
            favourite=False,
            created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        ))
        self.face_library_store.save(records)

    def _batch_item_failed(self, filename: str, message: str) -> None:
        self.batch_failed += 1
        self.batch_analysis.mark_failed(filename, message)

    def _batch_completed(self, succeeded: int, failed: int) -> None:
        self.batch_analysis.finish(succeeded, failed)
        self.face_library.refresh()
        self.status.showMessage(
            f"Batch analysis complete: {succeeded} succeeded, {failed} failed.",
            5000,
        )

    def _clear_batch_worker(self) -> None:
        self.batch_thread = None
        self.batch_worker = None

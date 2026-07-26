from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from facestudio.assets.scanner import AssetScanner, ScanResult


class AssetScanWorker(QObject):
    progress = Signal(int, str)
    completed = Signal(object)
    failed = Signal(str)
    finished = Signal()

    def __init__(self, root: Path) -> None:
        super().__init__()
        self.root = root
        self._cancelled = False

    @Slot()
    def run(self) -> None:
        try:
            result = AssetScanner().scan(
                self.root,
                progress_callback=self.progress.emit,
                cancel_check=lambda: self._cancelled,
            )
            self.completed.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            self.finished.emit()

    @Slot()
    def cancel(self) -> None:
        self._cancelled = True


class FaceAnalysisWorker(QObject):
    progress = Signal(str)
    completed = Signal(object, str, str)
    failed = Signal(str)
    finished = Signal()

    def __init__(self, source_path: Path, project_directory: Path) -> None:
        super().__init__()
        self.source_path = source_path
        self.project_directory = project_directory

    @Slot()
    def run(self) -> None:
        try:
            from facestudio.ai.service import FaceAnalysisService

            self.progress.emit("Loading face detector…")
            service = FaceAnalysisService()
            self.progress.emit("Detecting face and facial features…")
            analysis, analysis_path, preview_path = service.analyze_project_photo(
                self.source_path,
                self.project_directory,
            )
            self.completed.emit(
                analysis,
                str(analysis_path),
                str(preview_path),
            )
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            self.finished.emit()

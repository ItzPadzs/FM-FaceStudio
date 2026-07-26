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

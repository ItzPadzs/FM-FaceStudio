from __future__ import annotations

import json
import shutil
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot


class BatchAnalysisWorker(QObject):
    progress = Signal(int, int, str)
    item_completed = Signal(object)
    item_failed = Signal(str, str)
    completed = Signal(int, int)
    finished = Signal()

    def __init__(self, sources: list[Path], output_root: Path) -> None:
        super().__init__()
        self.sources = sources
        self.output_root = output_root
        self._cancelled = False

    @Slot()
    def run(self) -> None:
        succeeded = 0
        failed = 0
        try:
            from facestudio.ai.service import FaceAnalysisService

            self.output_root.mkdir(parents=True, exist_ok=True)
            service = FaceAnalysisService()
            total = len(self.sources)
            for index, source in enumerate(self.sources, start=1):
                if self._cancelled:
                    break
                self.progress.emit(index, total, source.name)
                safe_name = "".join(
                    char for char in source.stem if char not in '<>:"/\\|?*'
                ).strip() or f"face-{index}"
                item_directory = self.output_root / safe_name
                suffix = 2
                while item_directory.exists() and any(item_directory.iterdir()):
                    item_directory = self.output_root / f"{safe_name}-{suffix}"
                    suffix += 1
                item_directory.mkdir(parents=True, exist_ok=True)
                imported = item_directory / f"source{source.suffix.lower()}"
                try:
                    shutil.copy2(source, imported)
                    analysis, analysis_path, preview_path = service.analyze_project_photo(
                        imported, item_directory
                    )
                    payload = json.loads(analysis_path.read_text(encoding="utf-8"))
                    result = {
                        "name": source.stem,
                        "source_path": str(imported),
                        "preview_path": str(preview_path),
                        "analysis_path": str(analysis_path),
                        "face_shape": str(payload.get("face_shape", "undetermined")),
                        "confidence": float(payload.get("confidence", 0.0)),
                        "measurements": dict(payload.get("measurements", {})),
                    }
                    succeeded += 1
                    self.item_completed.emit(result)
                except Exception as exc:
                    failed += 1
                    self.item_failed.emit(source.name, str(exc))
            self.completed.emit(succeeded, failed)
        finally:
            self.finished.emit()

    @Slot()
    def cancel(self) -> None:
        self._cancelled = True

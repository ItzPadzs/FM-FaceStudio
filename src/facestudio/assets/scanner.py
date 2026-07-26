from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

from facestudio.assets.classifier import classify_asset
from facestudio.assets.models import AssetRecord


@dataclass(frozen=True, slots=True)
class ScanResult:
    root: Path
    records: tuple[AssetRecord, ...]
    skipped_files: int
    errors: tuple[str, ...]


class AssetScanner:
    def scan(
        self,
        root: Path,
        progress_callback: Callable[[int, str], None] | None = None,
        cancel_check: Callable[[], bool] | None = None,
    ) -> ScanResult:
        root = root.resolve()
        if not root.exists() or not root.is_dir():
            raise NotADirectoryError(root)

        records: list[AssetRecord] = []
        errors: list[str] = []
        skipped = 0
        visited = 0

        for current_root, directory_names, filenames in os.walk(root):
            directory_names[:] = [
                name for name in directory_names
                if name not in {".git", ".venv", "__pycache__"}
            ]

            if cancel_check and cancel_check():
                break

            current_path = Path(current_root)
            for filename in filenames:
                if cancel_check and cancel_check():
                    break

                visited += 1
                path = current_path / filename
                try:
                    stat = path.stat()
                    relative = path.relative_to(root).as_posix()
                    records.append(
                        AssetRecord(
                            path=path,
                            relative_path=relative,
                            filename=path.name,
                            extension=path.suffix.lower(),
                            asset_type=classify_asset(path),
                            size_bytes=stat.st_size,
                            modified_time=stat.st_mtime,
                        )
                    )
                except (OSError, ValueError) as exc:
                    skipped += 1
                    if len(errors) < 100:
                        errors.append(f"{path}: {exc}")

                if progress_callback and visited % 100 == 0:
                    progress_callback(visited, str(path))

        if progress_callback:
            progress_callback(visited, "Scan complete")

        return ScanResult(
            root=root,
            records=tuple(records),
            skipped_files=skipped,
            errors=tuple(errors),
        )

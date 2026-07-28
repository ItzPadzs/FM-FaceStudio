from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from facestudio.donor_asset_index import DONOR_INDEX_FORMAT, DonorAssetIndexer


@dataclass(frozen=True)
class AssetLibraryStatus:
    ready: bool
    index_path: Path | None
    donor_count: int
    message: str


class AssetLibraryManager:
    """Own FaceStudio's local donor library and hide JSON/index setup from users."""

    def __init__(self, data_directory: Path) -> None:
        self.data_directory = Path(data_directory).expanduser().resolve()
        self.library_directory = self.data_directory / "donor-library"
        self.index_directory = self.library_directory / "index"
        self.index_path = self.index_directory / "donor-asset-index.json"

    def status(self) -> AssetLibraryStatus:
        if not self.index_path.is_file():
            return AssetLibraryStatus(False, None, 0, "No donor library installed")
        try:
            payload = json.loads(self.index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return AssetLibraryStatus(False, None, 0, "The local donor index is damaged")
        if payload.get("format") != DONOR_INDEX_FORMAT:
            return AssetLibraryStatus(False, None, 0, "The local donor index is unsupported")
        count = int(payload.get("count") or len(payload.get("donors", [])))
        if count < 1:
            return AssetLibraryStatus(False, None, 0, "The donor library contains no usable textures")
        return AssetLibraryStatus(True, self.index_path, count, f"{count:,} donor textures ready")

    def import_folder(self, source: Path, *, names_file: Path | None = None) -> AssetLibraryStatus:
        source = Path(source).expanduser().resolve()
        if not source.is_dir():
            raise ValueError(f"Asset folder not found: {source}")
        self.index_directory.mkdir(parents=True, exist_ok=True)
        DonorAssetIndexer().build([source], self.index_directory, names_file=names_file)
        status = self.status()
        if not status.ready:
            raise RuntimeError(status.message)
        self._write_settings(source)
        return status

    def rebuild(self) -> AssetLibraryStatus:
        source = self._saved_source()
        if source is None:
            raise RuntimeError("No imported donor folder has been saved yet")
        return self.import_folder(source)

    def _write_settings(self, source: Path) -> None:
        self.library_directory.mkdir(parents=True, exist_ok=True)
        (self.library_directory / "library.json").write_text(
            json.dumps({"source": str(source)}, indent=2), encoding="utf-8"
        )

    def _saved_source(self) -> Path | None:
        path = self.library_directory / "library.json"
        if not path.is_file():
            return None
        try:
            source = Path(json.loads(path.read_text(encoding="utf-8"))["source"])
        except (OSError, KeyError, TypeError, json.JSONDecodeError):
            return None
        return source if source.is_dir() else None

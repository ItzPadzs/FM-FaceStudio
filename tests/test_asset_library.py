from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QColor, QImage

from facestudio.asset_library import AssetLibraryManager


def _texture(path: Path, colour: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image = QImage(1024, 1024, QImage.Format.Format_RGB32)
    image.fill(QColor(colour))
    assert image.save(str(path), "PNG")


def test_import_folder_builds_and_remembers_local_library(tmp_path: Path) -> None:
    source = tmp_path / "facepack"
    _texture(source / "heads" / "1001.png", "#a56f55")
    _texture(source / "heads" / "1002.png", "#654536")

    manager = AssetLibraryManager(tmp_path / "app-data")
    assert manager.status().ready is False

    status = manager.import_folder(source)
    assert status.ready is True
    assert status.donor_count == 2
    assert status.index_path is not None
    assert status.index_path.is_file()

    restarted = AssetLibraryManager(tmp_path / "app-data")
    assert restarted.status().ready is True
    assert restarted.rebuild().donor_count == 2

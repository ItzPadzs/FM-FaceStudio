from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QColor, QImage

from facestudio.donor_asset_index import DonorAssetIndexer
from facestudio.facestudio2_pipeline import FaceStudio2Pipeline


def _image(path: Path, colour: QColor, size: int = 256) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    image = QImage(size, size, QImage.Format.Format_RGB32)
    image.fill(colour)
    assert image.save(str(path), "PNG")
    return path


def test_pipeline_selects_donor_and_generates_changed_uv(tmp_path: Path) -> None:
    pack = tmp_path / "pack"
    donor = _image(pack / "1001.png", QColor(170, 110, 85), 512)
    _image(pack / "1002.png", QColor(45, 35, 30), 512)
    portrait = _image(tmp_path / "portrait.png", QColor(195, 135, 105), 384)
    index = DonorAssetIndexer().build([pack], tmp_path / "index")
    output = tmp_path / "generated.png"
    events = []

    result = FaceStudio2Pipeline(index).run(portrait, output, lambda *event: events.append(event))

    assert result.donor.donor_id == "1001"
    assert output.is_file()
    assert result.generation.engine == "regional-transfer-v1"
    assert result.generation.metadata["portrait_pixels_used"] is True
    assert QImage(str(output)) != QImage(str(donor))
    assert events[-1][0] == 100
    assert any(event[2] is not None for event in events)

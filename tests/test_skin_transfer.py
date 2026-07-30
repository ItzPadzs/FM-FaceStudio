from pathlib import Path

from PySide6.QtGui import QColor, QImage

from facestudio.ai.skin_transfer.compositor import composite
from facestudio.ai.skin_transfer.confidence import combine_confidence
from facestudio.ai.skin_transfer.pipeline import SkinTransferPipeline, SkinTransferRequest


def _image(path: Path, colour: QColor, size: int = 32) -> None:
    image = QImage(size, size, QImage.Format.Format_RGB32)
    image.fill(colour)
    assert image.save(str(path), "PNG")


def test_protected_pixels_remain_donor_exact() -> None:
    source = QImage(2, 1, QImage.Format.Format_RGB32)
    donor = QImage(2, 1, QImage.Format.Format_RGB32)
    candidate = QImage(2, 1, QImage.Format.Format_Grayscale8)
    protected = QImage(2, 1, QImage.Format.Format_Grayscale8)
    source.fill(QColor(220, 150, 110))
    donor.fill(QColor(40, 30, 20))
    candidate.fill(255)
    protected.fill(0)
    protected.setPixelColor(0, 0, QColor(255, 255, 255))

    confidence = combine_confidence(candidate, protected)
    result = composite(source, donor, confidence)

    assert result.pixelColor(0, 0) == donor.pixelColor(0, 0)
    assert result.pixelColor(1, 0) == source.pixelColor(1, 0)


def test_pipeline_exports_same_size_without_geometry_warp(tmp_path: Path) -> None:
    portrait = tmp_path / "portrait.png"
    donor = tmp_path / "donor.png"
    output = tmp_path / "result.png"
    diagnostics = tmp_path / "diagnostics"
    _image(portrait, QColor(160, 105, 75))
    _image(donor, QColor(120, 80, 60))

    result = SkinTransferPipeline().run(
        SkinTransferRequest(
            aligned_portrait=portrait,
            donor_texture=donor,
            output=output,
            diagnostics_dir=diagnostics,
        )
    )

    exported = QImage(str(output))
    assert exported.size() == QImage(str(donor)).size()
    assert result.metadata["geometry_warped"] is False
    assert len(result.diagnostics) == 6
    assert all(path.exists() for path in result.diagnostics)

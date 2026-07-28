from pathlib import Path

from PySide6.QtGui import QColor, QImage

from facestudio.ai.alignment_guard import AlignmentIdempotenceGuard
from facestudio.ai.generation_engine import GenerationRequest, GenerationSettings


def _texture(path: Path, colour: QColor) -> None:
    image = QImage(1024, 1024, QImage.Format.Format_RGB32)
    image.fill(colour)
    assert image.save(str(path), "PNG")


def test_exact_uv_is_bypassed_and_preserved(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    donor = tmp_path / "donor.png"
    output = tmp_path / "output.png"
    _texture(source, QColor(120, 85, 65))
    _texture(donor, QColor(120, 85, 65))

    guard = AlignmentIdempotenceGuard()
    decision = guard.inspect(source, donor)
    assert decision.bypass is True
    assert decision.mean_absolute_error == 0.0

    request = GenerationRequest(
        portrait=source,
        donor_texture=donor,
        output=output,
        donor_id="same",
        donor_name="same",
        settings=GenerationSettings(engine="unused", strength=1.0),
    )
    result = guard.passthrough(request, decision)
    assert result.metadata["alignment_bypassed"] is True
    assert QImage(str(output)) == QImage(str(source))


def test_normal_portrait_is_not_bypassed(tmp_path: Path) -> None:
    portrait = tmp_path / "portrait.png"
    donor = tmp_path / "donor.png"
    image = QImage(800, 1000, QImage.Format.Format_RGB32)
    image.fill(QColor(120, 85, 65))
    assert image.save(str(portrait), "PNG")
    _texture(donor, QColor(120, 85, 65))

    decision = AlignmentIdempotenceGuard().inspect(portrait, donor)
    assert decision.bypass is False
    assert "not a square" in decision.reason


def test_different_square_uv_is_not_bypassed(tmp_path: Path) -> None:
    portrait = tmp_path / "portrait.png"
    donor = tmp_path / "donor.png"
    _texture(portrait, QColor(220, 180, 150))
    _texture(donor, QColor(40, 30, 20))

    decision = AlignmentIdempotenceGuard().inspect(portrait, donor)
    assert decision.bypass is False
    assert decision.mean_absolute_error > decision.mean_absolute_error * 0 + AlignmentIdempotenceGuard.threshold

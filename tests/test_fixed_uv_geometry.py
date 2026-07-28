from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QColor, QImage

from facestudio.ai.fixed_uv_geometry import FM_FIXED_UV, FixedUVGeometry
from facestudio.ai.generation_engine import GenerationRequest, GenerationSettings
from facestudio.ai.unified_face_warp import UnifiedFaceWarpEngine


def _image(path: Path, colour: str, width: int, height: int) -> Path:
    image = QImage(width, height, QImage.Format.Format_ARGB32)
    image.fill(QColor(colour))
    assert image.save(str(path), "PNG")
    return path


def test_fixed_uv_profile_has_stable_1024_face_coordinates() -> None:
    rect = FM_FIXED_UV.face_rect(1024, 1024)
    assert rect.x() == 210
    assert rect.y() == 123
    assert rect.width() == 604
    assert rect.height() == 686
    assert FM_FIXED_UV.left_eye[0] < FM_FIXED_UV.right_eye[0]
    assert FM_FIXED_UV.nose[1] < FM_FIXED_UV.mouth[1] < FM_FIXED_UV.chin[1]


def test_invalid_non_square_profile_is_rejected() -> None:
    profile = FixedUVGeometry(width=1024, height=512)
    try:
        profile.validate()
    except ValueError as exc:
        assert "square" in str(exc)
    else:
        raise AssertionError("Expected non-square UV geometry to fail validation")


def test_unified_warp_always_exports_canonical_1024_texture(tmp_path: Path) -> None:
    portrait = _image(tmp_path / "portrait.png", "#8c5a43", 600, 800)
    donor = _image(tmp_path / "donor.png", "#bd8064", 512, 512)
    output = tmp_path / "generated.png"
    events: list[tuple[int, str, Path | None]] = []

    request = GenerationRequest(
        portrait=portrait,
        donor_texture=donor,
        output=output,
        settings=GenerationSettings(engine="unified-face-warp-v2"),
    )
    result = UnifiedFaceWarpEngine().generate(request, lambda *event: events.append(event))

    generated = QImage(str(output))
    assert generated.width() == 1024
    assert generated.height() == 1024
    assert result.metadata["uv_profile"] == "fm-fixed-front-face-v1"
    assert result.metadata["output_size"] == [1024, 1024]
    assert events[0][0] == 5
    assert events[-1][0] == 100
    assert any("continuous face" in message for _, message, _ in events)

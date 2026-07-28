from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtGui import QColor, QImage
import pytest

from facestudio.ai.generation_engine import (
    EngineRegistry,
    GENERATION_RECORD_FORMAT,
    GenerationRequest,
    GenerationSettings,
    TrainingCapture,
)


def _image(path: Path, colour: str, width: int = 64, height: int = 64) -> Path:
    image = QImage(width, height, QImage.Format.Format_RGB32)
    image.fill(QColor(colour))
    assert image.save(str(path), "PNG")
    return path


def test_baseline_engine_exports_selected_donor_and_reports_progress(tmp_path: Path) -> None:
    portrait = _image(tmp_path / "portrait.png", "#8b5a3c")
    donor = _image(tmp_path / "donor.png", "#c98f72", 128, 128)
    output = tmp_path / "generated.png"
    events: list[tuple[int, str, Path | None]] = []

    request = GenerationRequest(
        portrait=portrait,
        donor_texture=donor,
        output=output,
        donor_id="123",
        donor_name="Example Donor",
    )
    result = EngineRegistry().generate(request, lambda *event: events.append(event))

    assert output.is_file()
    exported = QImage(str(output))
    assert exported.size() == QImage(str(donor)).size()
    assert result.engine == "donor-baseline"
    assert result.metadata["identity_transfer"] is False
    assert events[0][0] == 5
    assert events[-1][0] == 100
    assert events[-1][2] == output.resolve()


def test_registry_rejects_unknown_engine(tmp_path: Path) -> None:
    portrait = _image(tmp_path / "portrait.png", "white")
    donor = _image(tmp_path / "donor.png", "black")
    request = GenerationRequest(
        portrait=portrait,
        donor_texture=donor,
        output=tmp_path / "result.png",
        settings=GenerationSettings(engine="missing-engine"),
    )

    with pytest.raises(ValueError, match="Unknown generation engine"):
        EngineRegistry().generate(request)


def test_request_validation_requires_png_output(tmp_path: Path) -> None:
    portrait = _image(tmp_path / "portrait.png", "white")
    donor = _image(tmp_path / "donor.png", "black")
    request = GenerationRequest(
        portrait=portrait,
        donor_texture=donor,
        output=tmp_path / "result.jpg",
    )

    with pytest.raises(ValueError, match="PNG"):
        request.validate()


def test_training_capture_writes_explicit_review_record(tmp_path: Path) -> None:
    portrait = _image(tmp_path / "portrait.png", "#70452f")
    donor = _image(tmp_path / "donor.png", "#b77b60")
    request = GenerationRequest(
        portrait=portrait,
        donor_texture=donor,
        output=tmp_path / "generated.png",
        donor_id="456",
        donor_name="Reviewed Donor",
    )
    result = EngineRegistry().generate(request)

    record = TrainingCapture().capture(
        tmp_path / "review",
        request,
        result,
        approved=True,
        notes="Reviewed in the desktop application",
        copy_assets=True,
    )
    payload = json.loads(record.read_text(encoding="utf-8"))

    assert payload["format"] == GENERATION_RECORD_FORMAT
    assert payload["approved"] is True
    assert payload["request"]["donor_id"] == "456"
    assert payload["result"]["engine"] == "donor-baseline"
    assert Path(payload["request"]["portrait"]).is_file()
    assert Path(payload["result"]["final_texture"]).is_file()

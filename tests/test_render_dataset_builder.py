from __future__ import annotations

import json
from pathlib import Path

import pytest
from PySide6.QtGui import QImage

from facestudio.match_engine_research.render_dataset_builder import RenderDatasetBuilder


def _write_png(path: Path, colour: int = 0xFF806050) -> None:
    image = QImage(1024, 1024, QImage.Format.Format_ARGB32)
    image.fill(colour)
    assert image.save(str(path), "PNG")


def test_scan_accepts_numeric_front_render_names(tmp_path: Path) -> None:
    _write_png(tmp_path / "100.png")
    _write_png(tmp_path / "200_front.png")
    _write_png(tmp_path / "not-a-player.png")

    candidates = RenderDatasetBuilder().scan(tmp_path)

    assert [item.player_id for item in candidates] == ["100", "200"]


def test_scan_rejects_duplicate_player_ids(tmp_path: Path) -> None:
    _write_png(tmp_path / "100.png")
    _write_png(tmp_path / "100_front.png")

    with pytest.raises(ValueError, match="Duplicate front render"):
        RenderDatasetBuilder().scan(tmp_path)


def test_record_requires_manual_landmark_review(tmp_path: Path) -> None:
    path = tmp_path / "100.png"
    _write_png(path)
    builder = RenderDatasetBuilder()
    candidate = builder.scan(tmp_path)[0]
    analysis = builder.analyse(candidate)

    with pytest.raises(ValueError, match="Correct at least one landmark"):
        builder.make_record(candidate, analysis)


def test_corrected_render_exports_valid_geometry_dataset(tmp_path: Path) -> None:
    path = tmp_path / "100_front.png"
    _write_png(path)
    builder = RenderDatasetBuilder()
    candidate = builder.scan(tmp_path)[0]
    analysis = builder.analyse(candidate)
    analysis = builder.move_landmark(analysis, "left_temple", 0.25, 0.30)
    record = builder.make_record(candidate, analysis, confidence=0.93)

    destination = builder.save((record,), tmp_path / "dataset")
    payload = json.loads(destination.read_text(encoding="utf-8"))

    assert payload["format"] == "facestudio-fm-head-geometry-v1"
    assert payload["records"][0]["player_id"] == "100"
    assert payload["records"][0]["source_type"] == "calibrated-render"
    assert payload["records"][0]["confidence"] == pytest.approx(0.93)

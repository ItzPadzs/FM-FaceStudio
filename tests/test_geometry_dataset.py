from __future__ import annotations

import json
from pathlib import Path

import pytest

from facestudio.match_engine_research.geometry_dataset import GeometryDatasetService
from facestudio.match_engine_research.one_click_face_builder import FaceMeasurements


def _measurements(face_width: float = 0.40, jaw_width: float = 0.32) -> dict[str, float]:
    return {
        "face_width": face_width,
        "face_height": 0.66,
        "eye_spacing": 0.18,
        "nose_length": 0.14,
        "mouth_width": 0.14,
        "jaw_width": jaw_width,
        "chin_length": 0.25,
        "symmetry": 0.95,
    }


def _write_dataset(path: Path) -> None:
    payload = {
        "format": "facestudio-fm-head-geometry-v1",
        "records": [
            {
                "player_id": "100",
                "source_type": "calibrated-render",
                "confidence": 0.90,
                "front_render": "100-front.png",
                "measurements": _measurements(0.40, 0.32),
            },
            {
                "player_id": "200",
                "source_type": "decoded-mesh",
                "confidence": 0.98,
                "measurements": _measurements(0.55, 0.48),
            },
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_dataset_loads_only_calibrated_records(tmp_path: Path) -> None:
    dataset = tmp_path / "geometry.json"
    _write_dataset(dataset)

    records = GeometryDatasetService().load(dataset)

    assert len(records) == 2
    assert records[0].player_id == "100"
    assert records[0].front_render == str((tmp_path / "100-front.png").resolve())
    assert records[1].source_type == "decoded-mesh"


def test_match_ranks_closest_comparable_geometry(tmp_path: Path) -> None:
    dataset = tmp_path / "geometry.json"
    _write_dataset(dataset)
    service = GeometryDatasetService()
    records = service.load(dataset)
    portrait = FaceMeasurements(**_measurements(0.41, 0.33))

    matches = service.match(portrait, records)

    assert matches[0].player_id == "100"
    assert matches[0].score > matches[1].score
    assert "jaw_width" in matches[0].component_differences


def test_dataset_rejects_uv_texture_as_geometry_source(tmp_path: Path) -> None:
    dataset = tmp_path / "bad.json"
    dataset.write_text(json.dumps({
        "format": "facestudio-fm-head-geometry-v1",
        "records": [{
            "player_id": "100",
            "source_type": "uv-texture",
            "confidence": 0.9,
            "measurements": _measurements(),
        }],
    }), encoding="utf-8")

    with pytest.raises(ValueError, match="calibrated-render or decoded-mesh"):
        GeometryDatasetService().load(dataset)


def test_dataset_rejects_duplicate_player_ids(tmp_path: Path) -> None:
    dataset = tmp_path / "duplicate.json"
    record = {
        "player_id": "100",
        "source_type": "calibrated-render",
        "confidence": 0.9,
        "measurements": _measurements(),
    }
    dataset.write_text(json.dumps({
        "format": "facestudio-fm-head-geometry-v1",
        "records": [record, record],
    }), encoding="utf-8")

    with pytest.raises(ValueError, match="Duplicate player_id"):
        GeometryDatasetService().load(dataset)

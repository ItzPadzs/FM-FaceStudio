from __future__ import annotations

import json
from pathlib import Path

from facestudio.match_engine_research.library_discovery import (
    INDEX_FORMAT, LibraryDiscoveryService, LibraryIndex,
)


def test_discovers_geometry_textures_profiles_and_projects(tmp_path: Path) -> None:
    geometry = tmp_path / "geometry.json"
    geometry.write_text(json.dumps({
        "format": "facestudio-fm-head-geometry-v1",
        "records": [{"player_id": "1"}, {"player_id": "2"}],
    }), encoding="utf-8")
    assets = tmp_path / "heads"; assets.mkdir(); (assets / "123.png").write_bytes(b"png")
    profiles = tmp_path / "profiles"; profiles.mkdir()
    (profiles / "123.json").write_text(json.dumps({
        "format": "facestudio-donor-uv-calibration-v1", "player_id": "123"
    }), encoding="utf-8")
    projects = tmp_path / "projects"; projects.mkdir()
    (projects / "build.json").write_text(json.dumps({
        "format": "facestudio-automatic-build-v2"
    }), encoding="utf-8")

    index = LibraryDiscoveryService().discover([tmp_path])

    assert index.geometry_dataset == str(geometry)
    assert index.geometry_records == 2
    assert index.donor_textures == 1
    assert index.uv_profiles == 1
    assert index.projects == 1
    assert index.donor_assets_directory == str(assets)


def test_library_index_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "index.json"
    original = LibraryIndex(roots=[str(tmp_path)], donor_textures=12, uv_profiles=4)
    original.save(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["format"] == INDEX_FORMAT
    loaded = LibraryIndex.load(path)
    assert loaded.roots == original.roots
    assert loaded.donor_textures == 12
    assert loaded.uv_profiles == 4


def test_largest_geometry_dataset_wins(tmp_path: Path) -> None:
    small = tmp_path / "small.json"; large = tmp_path / "large.json"
    small.write_text(json.dumps({"format": "facestudio-fm-head-geometry-v1", "records": [{}]}), encoding="utf-8")
    large.write_text(json.dumps({"format": "facestudio-fm-head-geometry-v1", "records": [{}, {}, {}]}), encoding="utf-8")
    index = LibraryDiscoveryService().discover([tmp_path])
    assert index.geometry_dataset == str(large)
    assert index.geometry_records == 3

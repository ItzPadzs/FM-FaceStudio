from __future__ import annotations

import json
from pathlib import Path

from facestudio.match_engine_research.automatic_face_builder import (
    AUTO_BUILD_FORMAT,
    AutomaticFaceBuilderService,
)


def test_find_uv_profile_requires_complete_matching_player(tmp_path: Path) -> None:
    wrong = tmp_path / "wrong.json"
    wrong.write_text(json.dumps({
        "format": "facestudio-donor-uv-calibration-v1",
        "player_id": "100",
        "complete": True,
    }), encoding="utf-8")
    incomplete = tmp_path / "200.json"
    incomplete.write_text(json.dumps({
        "format": "facestudio-donor-uv-calibration-v1",
        "player_id": "200",
        "complete": False,
    }), encoding="utf-8")
    valid = tmp_path / "nested" / "200-profile.json"
    valid.parent.mkdir()
    valid.write_text(json.dumps({
        "format": "facestudio-donor-uv-calibration-v1",
        "player_id": "200",
        "complete": True,
    }), encoding="utf-8")

    assert AutomaticFaceBuilderService._find_uv_profile(tmp_path, "200") == valid
    assert AutomaticFaceBuilderService._find_uv_profile(tmp_path, "300") is None


def test_automatic_build_format_is_versioned() -> None:
    assert AUTO_BUILD_FORMAT == "facestudio-automatic-build-v1"

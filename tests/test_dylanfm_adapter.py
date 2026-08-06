from __future__ import annotations

import json
from pathlib import Path

from facestudio.integrations.dylanfm_adapter import DylanFmAdapter


def test_parse_active_player_payload() -> None:
    selection = DylanFmAdapter.parse_selection(
        {
            "activePlayer": {
                "playerId": "37055843",
                "playerName": "Matthijs de Ligt",
                "clubName": "Manchester United",
                "nationality": "Netherlands",
            }
        }
    )
    assert selection is not None
    assert selection.id == 37055843
    assert selection.name == "Matthijs de Ligt"
    assert selection.club == "Manchester United"
    assert selection.nation == "Netherlands"


def test_publish_latest_public_output(tmp_path: Path) -> None:
    source = tmp_path / "dylan"
    source.mkdir()
    bridge = tmp_path / "bridge"
    (source / "active-player.json").write_text(
        json.dumps({"player_id": 7458500, "player_name": "Lionel Messi"}),
        encoding="utf-8",
    )

    adapter = DylanFmAdapter(extra_roots=[source], bridge_root=bridge)
    selection = adapter.publish_once()

    assert selection is not None
    published = json.loads((bridge / "selected-player.json").read_text(encoding="utf-8"))
    assert published["id"] == 7458500
    assert published["name"] == "Lionel Messi"
    assert published["source"].startswith("dylanfm-public-output:")


def test_invalid_payload_is_ignored(tmp_path: Path) -> None:
    source = tmp_path / "dylan"
    source.mkdir()
    bridge = tmp_path / "bridge"
    (source / "ui-probe.json").write_text(json.dumps({"clues": 29}), encoding="utf-8")

    adapter = DylanFmAdapter(extra_roots=[source], bridge_root=bridge)
    assert adapter.publish_once() is None
    assert not (bridge / "selected-player.json").exists()

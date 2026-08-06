from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

from facestudio.fm_bridge import FaceStudioBridgeClient


def test_connected_status_requires_fresh_heartbeat(tmp_path: Path) -> None:
    client = FaceStudioBridgeClient(tmp_path)
    tmp_path.mkdir(parents=True)
    client.status_path.write_text(
        json.dumps(
            {
                "version": "0.1.0",
                "state": "connected",
                "processId": 123,
                "updatedAtUtc": datetime.now(timezone.utc).isoformat(),
                "error": None,
            }
        ),
        encoding="utf-8",
    )

    status = client.status()
    assert status is not None
    assert status.connected
    assert status.process_id == 123


def test_selected_player_parses_transport_file(tmp_path: Path) -> None:
    client = FaceStudioBridgeClient(tmp_path)
    tmp_path.mkdir(parents=True)
    client.selected_player_path.write_text(
        json.dumps(
            {
                "id": 37055843,
                "name": "Matthijs de Ligt",
                "club": "Manchester United",
                "nation": "Netherlands",
                "source": "test",
            }
        ),
        encoding="utf-8",
    )

    player = client.selected_player()
    assert player is not None
    assert player.player_id == 37055843
    assert player.name == "Matthijs de Ligt"


def test_install_plugin_rejects_non_fm_executable(tmp_path: Path) -> None:
    plugin = tmp_path / "FMFaceStudioBridge.dll"
    plugin.write_bytes(b"dll")
    wrong_executable = tmp_path / "not-fm.exe"
    wrong_executable.write_bytes(b"exe")

    try:
        FaceStudioBridgeClient.install_plugin(plugin, wrong_executable)
    except ValueError as exc:
        assert "fm.exe" in str(exc)
    else:
        raise AssertionError("Expected invalid executable to be rejected")

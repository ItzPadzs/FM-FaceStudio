from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import time
import uuid


@dataclass(frozen=True)
class BridgeStatus:
    version: str
    state: str
    process_id: int
    updated_at_utc: str
    error: str | None = None

    @property
    def connected(self) -> bool:
        if self.state != "connected":
            return False
        try:
            updated = datetime.fromisoformat(self.updated_at_utc.replace("Z", "+00:00"))
        except ValueError:
            return False
        return (datetime.now(timezone.utc) - updated).total_seconds() <= 5.0


@dataclass(frozen=True)
class PlayerSelection:
    player_id: int
    name: str
    club: str | None = None
    nation: str | None = None
    source: str | None = None
    captured_at_utc: str | None = None


class FaceStudioBridgeClient:
    """File-based transport shared with the BepInEx bridge plugin.

    All mutable files live under LocalAppData rather than Program Files, avoiding
    the access-denied failure seen when third-party plugins write into the game
    installation directory.
    """

    def __init__(self, root: Path | None = None) -> None:
        self.root = Path(root) if root else Path.home() / "AppData" / "Local" / "FM-FaceStudio" / "bridge"
        self.commands = self.root / "commands"
        self.responses = self.root / "responses"
        self.status_path = self.root / "status.json"
        self.selected_player_path = self.root / "selected-player.json"

    def status(self) -> BridgeStatus | None:
        payload = self._read_json(self.status_path)
        if payload is None:
            return None
        return BridgeStatus(
            version=str(payload.get("version", "")),
            state=str(payload.get("state", "unknown")),
            process_id=int(payload.get("processId", 0)),
            updated_at_utc=str(payload.get("updatedAtUtc", "")),
            error=payload.get("error"),
        )

    def selected_player(self) -> PlayerSelection | None:
        payload = self._read_json(self.selected_player_path)
        if payload is None:
            return None
        player_id = int(payload.get("id", 0))
        name = str(payload.get("name", "")).strip()
        if player_id <= 0 or not name:
            return None
        return PlayerSelection(
            player_id=player_id,
            name=name,
            club=payload.get("club"),
            nation=payload.get("nation"),
            source=payload.get("source"),
            captured_at_utc=payload.get("capturedAtUtc"),
        )

    def ping(self, timeout: float = 4.0) -> bool:
        response = self.send_command({"type": "ping"}, timeout=timeout)
        return bool(response and response.get("success") and response.get("message") == "pong")

    def publish_player(
        self,
        player_id: int,
        name: str,
        *,
        club: str | None = None,
        nation: str | None = None,
        source: str = "facestudio-desktop",
        timeout: float = 4.0,
    ) -> bool:
        response = self.send_command(
            {
                "type": "publish-player",
                "player": {
                    "id": int(player_id),
                    "name": name.strip(),
                    "club": club,
                    "nation": nation,
                    "source": source,
                },
            },
            timeout=timeout,
        )
        return bool(response and response.get("success"))

    def send_command(self, command: dict, *, timeout: float = 4.0) -> dict | None:
        self.commands.mkdir(parents=True, exist_ok=True)
        self.responses.mkdir(parents=True, exist_ok=True)
        command_id = uuid.uuid4().hex
        payload = dict(command)
        payload["id"] = command_id
        command_path = self.commands / f"{command_id}.json"
        response_path = self.responses / f"{command_id}.json"
        self._atomic_write(command_path, payload)

        deadline = time.monotonic() + max(timeout, 0.1)
        while time.monotonic() < deadline:
            response = self._read_json(response_path)
            if response is not None:
                response_path.unlink(missing_ok=True)
                return response
            time.sleep(0.05)
        return None

    @staticmethod
    def install_plugin(plugin_dll: Path, fm_executable: Path) -> Path:
        plugin_dll = Path(plugin_dll).expanduser().resolve()
        fm_executable = Path(fm_executable).expanduser().resolve()
        if not plugin_dll.is_file() or plugin_dll.suffix.lower() != ".dll":
            raise ValueError("Choose the compiled FMFaceStudioBridge.dll file")
        if not fm_executable.is_file() or fm_executable.name.lower() != "fm.exe":
            raise ValueError("Choose Football Manager's fm.exe file")

        bepinex = fm_executable.parent / "BepInEx"
        if not (bepinex / "core" / "BepInEx.Core.dll").is_file():
            raise FileNotFoundError("BepInEx was not found beside the selected fm.exe")

        destination = bepinex / "plugins" / "FMFaceStudioBridge"
        destination.mkdir(parents=True, exist_ok=True)
        installed = destination / "FMFaceStudioBridge.dll"
        shutil.copy2(plugin_dll, installed)
        return installed

    @staticmethod
    def _read_json(path: Path) -> dict | None:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return None

    @staticmethod
    def _atomic_write(path: Path, payload: dict) -> None:
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        temporary.replace(path)

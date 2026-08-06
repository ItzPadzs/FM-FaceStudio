from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True)
class PlayerSelection:
    id: int
    name: str
    club: str | None = None
    nation: str | None = None
    source: str = "dylanfm-public-output"

    def to_bridge_payload(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "club": self.club,
            "nation": self.nation,
            "source": self.source,
            "capturedAtUtc": None,
        }


KNOWN_OUTPUT_NAMES = (
    "active-player.json",
    "native-selection-probe.json",
    "ui-probe.json",
)


class DylanFmAdapter:
    """Consume DylanFM's observable JSON outputs without loading its DLL.

    This adapter deliberately treats DylanFM as an external producer. It does not
    decompile, patch, reflect over or redistribute DylanFM binaries. It only reads
    JSON files DylanFM writes to disk and republishes a validated selection in the
    FM-FaceStudio bridge format.
    """

    def __init__(
        self,
        *,
        fm_root: Path | None = None,
        extra_roots: Iterable[Path] = (),
        bridge_root: Path | None = None,
    ) -> None:
        self.fm_root = Path(fm_root).resolve() if fm_root else None
        self.extra_roots = tuple(Path(path).resolve() for path in extra_roots)
        self.bridge_root = bridge_root or (
            Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
            / "FM-FaceStudio"
            / "bridge"
        )
        self.bridge_root = Path(self.bridge_root)
        self.selected_player_path = self.bridge_root / "selected-player.json"
        self.status_path = self.bridge_root / "dylanfm-adapter-status.json"
        self._last_signature: tuple[int, str] | None = None

    def candidate_roots(self) -> tuple[Path, ...]:
        roots: list[Path] = []
        if self.fm_root:
            roots.extend(
                [
                    self.fm_root,
                    self.fm_root / "BepInEx" / "plugins",
                    self.fm_root / "BepInEx" / "plugins" / "DylanFMPlayerRadar",
                    self.fm_root / "heads",
                    self.fm_root / "heads_cache",
                    self.fm_root / "hh2_requests",
                ]
            )

        local = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        documents = Path.home() / "Documents"
        roots.extend(
            [
                local / "DylanFM",
                local / "DylanFM FaceStudio",
                local / "FM-FaceStudio",
                documents / "Sports Interactive" / "Football Manager 26",
            ]
        )
        roots.extend(self.extra_roots)

        unique: list[Path] = []
        seen: set[str] = set()
        for root in roots:
            key = str(root).casefold()
            if key not in seen:
                seen.add(key)
                unique.append(root)
        return tuple(unique)

    def discover_outputs(self) -> list[Path]:
        found: list[Path] = []
        for root in self.candidate_roots():
            if not root.exists():
                continue
            for name in KNOWN_OUTPUT_NAMES:
                direct = root / name
                if direct.is_file():
                    found.append(direct)
            try:
                for path in root.rglob("*.json"):
                    if path.name.casefold() in {name.casefold() for name in KNOWN_OUTPUT_NAMES}:
                        found.append(path)
            except (OSError, PermissionError):
                continue
        return sorted(set(found), key=lambda path: path.stat().st_mtime, reverse=True)

    @staticmethod
    def _first(payload: dict[str, Any], *keys: str) -> Any:
        lowered = {str(key).casefold(): value for key, value in payload.items()}
        for key in keys:
            if key.casefold() in lowered:
                return lowered[key.casefold()]
        return None

    @classmethod
    def parse_selection(cls, payload: Any) -> PlayerSelection | None:
        if not isinstance(payload, dict):
            return None

        nested_candidates = [payload]
        for key in ("player", "activePlayer", "active_player", "selection", "payload"):
            value = payload.get(key)
            if isinstance(value, dict):
                nested_candidates.append(value)

        for candidate in nested_candidates:
            raw_id = cls._first(
                candidate,
                "id",
                "playerId",
                "player_id",
                "uid",
                "playerUid",
                "player_uid",
            )
            raw_name = cls._first(candidate, "name", "playerName", "player_name", "displayName")
            try:
                player_id = int(str(raw_id).strip())
            except (TypeError, ValueError):
                continue
            name = str(raw_name or "").strip()
            if player_id <= 0 or not name:
                continue

            club = cls._first(candidate, "club", "clubName", "club_name", "team")
            nation = cls._first(candidate, "nation", "nationality", "nationName", "nation_name")
            return PlayerSelection(
                id=player_id,
                name=name,
                club=str(club).strip() if club else None,
                nation=str(nation).strip() if nation else None,
            )
        return None

    def read_latest_selection(self) -> tuple[PlayerSelection, Path] | None:
        for path in self.discover_outputs():
            try:
                payload = json.loads(path.read_text(encoding="utf-8-sig"))
            except (OSError, UnicodeError, json.JSONDecodeError):
                continue
            selection = self.parse_selection(payload)
            if selection:
                return selection, path
        return None

    @staticmethod
    def _atomic_write(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        temporary.replace(path)

    def publish_once(self) -> PlayerSelection | None:
        result = self.read_latest_selection()
        if result is None:
            self._atomic_write(
                self.status_path,
                {"state": "waiting", "message": "No valid DylanFM player output found."},
            )
            return None

        selection, source_path = result
        signature = (selection.id, selection.name.casefold())
        if signature == self._last_signature:
            return selection

        payload = selection.to_bridge_payload()
        payload["source"] = f"dylanfm-public-output:{source_path.name}"
        self._atomic_write(self.selected_player_path, payload)
        self._atomic_write(
            self.status_path,
            {
                "state": "published",
                "playerId": selection.id,
                "playerName": selection.name,
                "sourcePath": str(source_path),
            },
        )
        self._last_signature = signature
        return selection

    def run(self, *, interval_seconds: float = 0.75) -> None:
        while True:
            self.publish_once()
            time.sleep(max(0.2, interval_seconds))

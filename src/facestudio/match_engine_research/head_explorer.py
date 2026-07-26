from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path


PLAYER_FILE_RE = re.compile(
    r"^(?P<player_id>\d+)(?P<variant>_(?:hair|hair2))?\.(?P<extension>png|cfg2|skin)$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class BinarySummary:
    path: str
    size_bytes: int
    sha256: str
    header_hex: str
    little_endian_u32: tuple[int, ...]


@dataclass(frozen=True)
class HeadRecord:
    player_id: str
    player_name: str
    face_png: str | None
    config_cfg2: str | None
    skin_file: str | None
    hair_png: str | None
    hair2_png: str | None
    hair_skin: str | None
    cfg2_values: dict[str, str]
    cfg2_comments: tuple[str, ...]
    skin_summary: BinarySummary | None

    @property
    def available_assets(self) -> int:
        return sum(
            value is not None
            for value in (
                self.face_png,
                self.config_cfg2,
                self.skin_file,
                self.hair_png,
                self.hair2_png,
                self.hair_skin,
            )
        )


@dataclass(frozen=True)
class HeadLibrary:
    root: str
    players_file: str | None
    records: tuple[HeadRecord, ...]
    warnings: tuple[str, ...]


class HeadExplorerService:
    """Read-only interpreter for observed FM26 loose head-cache layouts.

    The service groups files by numeric player ID and records only structures
    we can demonstrate from the loose files. It does not claim to decode the
    proprietary meaning of the binary ``.skin`` payload.
    """

    HEADER_BYTES = 64
    UINT32_COUNT = 8

    def load(self, root: Path) -> HeadLibrary:
        root = root.expanduser().resolve()
        if not root.is_dir():
            raise ValueError("Select a heads folder that exists.")

        warnings: list[str] = []
        players_path = root / "_players.json"
        players = self._load_players(players_path, warnings)
        grouped: dict[str, dict[str, Path]] = {}

        for path in sorted(item for item in root.iterdir() if item.is_file()):
            match = PLAYER_FILE_RE.match(path.name)
            if not match:
                continue
            player_id = match.group("player_id")
            variant = (match.group("variant") or "").lower()
            extension = match.group("extension").lower()
            key = self._asset_key(extension, variant)
            if key is None:
                continue
            group = grouped.setdefault(player_id, {})
            if key in group:
                warnings.append(f"{player_id}: duplicate {key} file ({path.name})")
                continue
            group[key] = path

        all_ids = sorted(set(players) | set(grouped), key=lambda value: int(value))
        records: list[HeadRecord] = []
        for player_id in all_ids:
            assets = grouped.get(player_id, {})
            cfg_path = assets.get("config_cfg2")
            cfg_values: dict[str, str] = {}
            cfg_comments: tuple[str, ...] = ()
            if cfg_path is not None:
                try:
                    cfg_values, cfg_comments = self.parse_cfg2(cfg_path)
                except (OSError, UnicodeError) as exc:
                    warnings.append(f"{cfg_path.name}: could not read CFG2 ({exc})")

            skin_path = assets.get("skin_file")
            skin_summary = None
            if skin_path is not None:
                try:
                    skin_summary = self.inspect_binary(skin_path, root)
                except OSError as exc:
                    warnings.append(f"{skin_path.name}: could not inspect SKIN ({exc})")

            records.append(
                HeadRecord(
                    player_id=player_id,
                    player_name=players.get(player_id, "Unknown player"),
                    face_png=self._relative(assets.get("face_png"), root),
                    config_cfg2=self._relative(cfg_path, root),
                    skin_file=self._relative(skin_path, root),
                    hair_png=self._relative(assets.get("hair_png"), root),
                    hair2_png=self._relative(assets.get("hair2_png"), root),
                    hair_skin=self._relative(assets.get("hair_skin"), root),
                    cfg2_values=cfg_values,
                    cfg2_comments=cfg_comments,
                    skin_summary=skin_summary,
                )
            )

        return HeadLibrary(
            root=str(root),
            players_file=str(players_path) if players_path.is_file() else None,
            records=tuple(records),
            warnings=tuple(warnings),
        )

    def parse_cfg2(self, path: Path) -> tuple[dict[str, str], tuple[str, ...]]:
        values: dict[str, str] = {}
        comments: list[str] = []
        for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith("#"):
                comments.append(line[1:].strip())
                continue
            if "=" not in line:
                comments.append(f"Unparsed line {line_number}: {line}")
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if not key:
                comments.append(f"Unparsed line {line_number}: {line}")
                continue
            values[key] = value.strip()
        return values, tuple(comments)

    def inspect_binary(self, path: Path, root: Path | None = None) -> BinarySummary:
        content = path.read_bytes()
        header = content[: self.HEADER_BYTES]
        words: list[int] = []
        for offset in range(0, min(len(header), self.UINT32_COUNT * 4), 4):
            chunk = header[offset : offset + 4]
            if len(chunk) == 4:
                words.append(int.from_bytes(chunk, byteorder="little", signed=False))
        display_path = path.name if root is None else path.relative_to(root).as_posix()
        return BinarySummary(
            path=display_path,
            size_bytes=len(content),
            sha256=hashlib.sha256(content).hexdigest(),
            header_hex=header.hex(" "),
            little_endian_u32=tuple(words),
        )

    def export_library(self, library: HeadLibrary, destination: Path) -> Path:
        destination = destination.expanduser()
        destination.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema": "facestudio-fm26-head-library-v1",
            "scope": "Read-only grouping and structural inspection of user-selected loose head files.",
            "root": library.root,
            "players_file": library.players_file,
            "record_count": len(library.records),
            "records": [asdict(record) for record in library.records],
            "warnings": list(library.warnings),
        }
        destination.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return destination

    def _load_players(self, path: Path, warnings: list[str]) -> dict[str, str]:
        if not path.is_file():
            warnings.append("_players.json was not found; names will be shown as unknown.")
            return {}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            warnings.append(f"_players.json could not be read ({exc})")
            return {}
        if not isinstance(payload, dict):
            warnings.append("_players.json is not a JSON object.")
            return {}
        result: dict[str, str] = {}
        for key, value in payload.items():
            player_id = str(key).strip()
            if not player_id.isdigit() or not isinstance(value, str):
                warnings.append(f"Ignored invalid player entry: {key!r}")
                continue
            result[player_id] = value
        return result

    @staticmethod
    def _asset_key(extension: str, variant: str) -> str | None:
        if extension == "cfg2" and not variant:
            return "config_cfg2"
        if extension == "skin" and variant == "_hair":
            return "hair_skin"
        if extension == "skin" and not variant:
            return "skin_file"
        if extension == "png" and variant == "_hair":
            return "hair_png"
        if extension == "png" and variant == "_hair2":
            return "hair2_png"
        if extension == "png" and not variant:
            return "face_png"
        return None

    @staticmethod
    def _relative(path: Path | None, root: Path) -> str | None:
        return None if path is None else path.relative_to(root).as_posix()

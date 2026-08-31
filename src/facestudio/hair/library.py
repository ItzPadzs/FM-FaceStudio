from __future__ import annotations

import json
from pathlib import Path
import re

from facestudio.hair.models import HairAssetContract, HairCandidate, HairDescriptor
from facestudio.hair.skin import HairSkinError, describe_hair_skin


_UID_HAIR_RE = re.compile(r"^(?P<uid>.+?)_hair\.skin$", re.IGNORECASE)


class HairLibrary:
    """Indexes native FM hair sets without modifying their asset contracts."""

    def __init__(self, cache_path: Path | None = None, proven_path: Path | None = None) -> None:
        self.cache_path = cache_path
        self.proven_path = proven_path

    @staticmethod
    def _find_companion(directory: Path, filename: str) -> Path | None:
        candidate = directory / filename
        return candidate if candidate.is_file() else None

    @staticmethod
    def _load_player_names(root: Path) -> dict[str, str]:
        candidates = list(root.rglob("_players.json"))[:4]
        merged: dict[str, str] = {}
        for path in candidates:
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError, TypeError):
                continue
            if isinstance(payload, dict):
                for key, value in payload.items():
                    if isinstance(value, str):
                        merged[str(key)] = value
        return merged

    def _load_cache(self) -> dict[str, dict]:
        if not self.cache_path or not self.cache_path.is_file():
            return {}
        try:
            payload = json.loads(self.cache_path.read_text(encoding="utf-8"))
            return payload if isinstance(payload, dict) else {}
        except (OSError, ValueError, TypeError):
            return {}

    def _save_cache(self, payload: dict[str, dict]) -> None:
        if not self.cache_path:
            return
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.cache_path.with_suffix(self.cache_path.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        temporary.replace(self.cache_path)

    def _load_proven(self) -> set[str]:
        if not self.proven_path or not self.proven_path.is_file():
            return set()
        try:
            payload = json.loads(self.proven_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return set()
        values = payload.get("proven_hair", []) if isinstance(payload, dict) else []
        return {str(value) for value in values}

    def set_proven(self, candidate_id: str, proven: bool = True) -> None:
        if not self.proven_path:
            return
        values = self._load_proven()
        if proven:
            values.add(candidate_id)
        else:
            values.discard(candidate_id)
        self.proven_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.proven_path.with_suffix(self.proven_path.suffix + ".tmp")
        temporary.write_text(
            json.dumps({"schema_version": 1, "proven_hair": sorted(values)}, indent=2),
            encoding="utf-8",
        )
        temporary.replace(self.proven_path)

    @staticmethod
    def _descriptor_from_payload(payload: dict) -> HairDescriptor:
        return HairDescriptor(
            vertex_count=int(payload["vertex_count"]),
            triangle_count=int(payload["triangle_count"]),
            component_count=int(payload["component_count"]),
            width_height_ratio=float(payload["width_height_ratio"]),
            depth_height_ratio=float(payload["depth_height_ratio"]),
            width_depth_ratio=float(payload["width_depth_ratio"]),
            centroid_y_ratio=float(payload["centroid_y_ratio"]),
            front_occupancy=tuple(int(value) for value in payload["front_occupancy"]),
            side_occupancy=tuple(int(value) for value in payload["side_occupancy"]),
            top_occupancy=tuple(int(value) for value in payload["top_occupancy"]),
            uv_outside_fraction=float(payload.get("uv_outside_fraction", 0.0)),
        )

    def scan(self, root: str | Path) -> list[HairCandidate]:
        root = Path(root).expanduser().resolve()
        if not root.is_dir():
            raise ValueError(f"Hair library folder does not exist: {root}")

        names = self._load_player_names(root)
        proven = self._load_proven()
        cache = self._load_cache()
        new_cache: dict[str, dict] = {}
        candidates: list[HairCandidate] = []

        for skin in sorted(root.rglob("*_hair.skin"), key=lambda p: str(p).lower()):
            match = _UID_HAIR_RE.match(skin.name)
            if not match:
                continue
            uid = match.group("uid")
            stat = skin.stat()
            key = str(skin)
            cached = cache.get(key)
            descriptor: HairDescriptor
            if (
                cached
                and cached.get("size") == stat.st_size
                and cached.get("mtime_ns") == stat.st_mtime_ns
                and isinstance(cached.get("descriptor"), dict)
            ):
                try:
                    descriptor = self._descriptor_from_payload(cached["descriptor"])
                except (KeyError, TypeError, ValueError):
                    descriptor = describe_hair_skin(skin)
            else:
                try:
                    descriptor = describe_hair_skin(skin)
                except HairSkinError:
                    continue

            directory = skin.parent
            contract = HairAssetContract(
                uid=uid,
                root=directory,
                skin=skin,
                diffuse=self._find_companion(directory, f"{uid}_hair2.png"),
                normal=self._find_companion(directory, f"{uid}_hair_nrm.png"),
                normal2=self._find_companion(directory, f"{uid}_hair2_nrm.png"),
                cfg2=self._find_companion(directory, f"{uid}.cfg2"),
            )
            display_name = names.get(uid) or directory.name or uid
            candidate_id = f"fm:{uid}:{skin.relative_to(root).as_posix()}"
            notes: list[str] = []
            if not contract.complete:
                notes.append("missing diffuse")
            if not contract.normal_files:
                notes.append("no normal map supplied")
            if descriptor.uv_outside_fraction > 0:
                notes.append("native UVs extend outside 0-1; preserve them")

            candidates.append(
                HairCandidate(
                    candidate_id=candidate_id,
                    display_name=display_name,
                    contract=contract,
                    descriptor=descriptor,
                    proven=(candidate_id in proven or uid in proven),
                    notes="; ".join(notes),
                )
            )
            new_cache[key] = {
                "size": stat.st_size,
                "mtime_ns": stat.st_mtime_ns,
                "descriptor": descriptor.to_dict(),
            }

        self._save_cache(new_cache)
        return candidates

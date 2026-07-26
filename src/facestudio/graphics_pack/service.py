from __future__ import annotations

import json
import shutil
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from facestudio.image_studio.service import ImageStudioService


@dataclass(slots=True)
class GraphicsPackEntry:
    id: str
    image_record_id: str
    unique_id: str
    display_name: str
    enabled: bool = True

    @classmethod
    def from_dict(cls, payload: dict) -> "GraphicsPackEntry":
        return cls(
            id=str(payload.get("id") or uuid4()),
            image_record_id=str(payload.get("image_record_id", "")),
            unique_id=str(payload.get("unique_id", "")).strip(),
            display_name=str(payload.get("display_name", "Untitled")),
            enabled=bool(payload.get("enabled", True)),
        )


class GraphicsPackService:
    """Builds standard user graphics folders from FaceStudio image exports and user-supplied IDs."""

    def __init__(self, data_dir: Path, image_service: ImageStudioService) -> None:
        self.data_dir = data_dir
        self.image_service = image_service
        self.store_path = data_dir / "graphics-pack-project.json"

    def load_entries(self) -> list[GraphicsPackEntry]:
        if not self.store_path.exists():
            return []
        try:
            payload = json.loads(self.store_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError):
            return []
        items = payload.get("entries", []) if isinstance(payload, dict) else []
        return [GraphicsPackEntry.from_dict(item) for item in items if isinstance(item, dict)]

    def save_entries(self, entries: list[GraphicsPackEntry]) -> None:
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema": 1,
            "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "entries": [asdict(item) for item in entries],
        }
        temporary = self.store_path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        temporary.replace(self.store_path)

    def sync_from_image_library(self) -> tuple[int, int]:
        records = self.image_service.load()
        entries = self.load_entries()
        known = {entry.image_record_id for entry in entries}
        added = 0
        for record in records:
            if record.id in known:
                continue
            entries.append(GraphicsPackEntry(
                id=str(uuid4()),
                image_record_id=record.id,
                unique_id="",
                display_name=record.name,
            ))
            added += 1
        valid_ids = {record.id for record in records}
        before = len(entries)
        entries = [entry for entry in entries if entry.image_record_id in valid_ids]
        removed = before - len(entries)
        self.save_entries(entries)
        return added, removed

    def update_entry(self, entry: GraphicsPackEntry) -> None:
        entries = self.load_entries()
        for index, current in enumerate(entries):
            if current.id == entry.id:
                entries[index] = entry
                break
        self.save_entries(entries)

    def validate(self, entries: list[GraphicsPackEntry] | None = None) -> list[str]:
        entries = entries or self.load_entries()
        records = {item.id: item for item in self.image_service.load()}
        issues: list[str] = []
        seen: dict[str, str] = {}
        for entry in entries:
            if not entry.enabled:
                continue
            label = entry.display_name or entry.id
            if not entry.unique_id:
                issues.append(f"{label}: missing Football Manager unique ID")
            elif not entry.unique_id.isdigit():
                issues.append(f"{label}: unique ID must contain digits only")
            elif entry.unique_id in seen:
                issues.append(f"{label}: duplicate unique ID also used by {seen[entry.unique_id]}")
            else:
                seen[entry.unique_id] = label
            record = records.get(entry.image_record_id)
            if record is None:
                issues.append(f"{label}: linked Image Studio record is missing")
            elif not Path(record.source_path).exists():
                issues.append(f"{label}: source image is missing")
        if not any(entry.enabled for entry in entries):
            issues.append("No enabled entries are available to build.")
        return issues

    def build_pack(self, destination: Path, pack_name: str) -> dict[str, object]:
        safe_name = "".join(character for character in pack_name.strip() if character not in '<>:"/\\|?*').strip()
        if not safe_name:
            raise ValueError("Enter a valid pack name.")
        entries = self.load_entries()
        issues = self.validate(entries)
        if issues:
            raise ValueError("Fix validation issues before building the pack.")
        records = {item.id: item for item in self.image_service.load()}
        pack_dir = destination / safe_name
        faces_dir = pack_dir / "faces"
        faces_dir.mkdir(parents=True, exist_ok=True)

        copied = 0
        mappings: list[tuple[str, str]] = []
        manifest_entries: list[dict[str, str]] = []
        for entry in entries:
            if not entry.enabled:
                continue
            record = records[entry.image_record_id]
            record.output_format = "PNG"
            exported = self.image_service.export(record, faces_dir)
            target = faces_dir / f"{entry.unique_id}.png"
            if exported != target:
                if target.exists():
                    target.unlink()
                shutil.move(str(exported), str(target))
                sidecar = exported.with_suffix(exported.suffix + ".json")
                if sidecar.exists():
                    sidecar.unlink()
            mappings.append((entry.unique_id, f"faces/{entry.unique_id}"))
            manifest_entries.append({
                "unique_id": entry.unique_id,
                "display_name": entry.display_name,
                "file": f"faces/{entry.unique_id}.png",
            })
            copied += 1

        self._write_config(pack_dir / "config.xml", mappings)
        manifest = {
            "name": safe_name,
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "generator": "FM FaceStudio",
            "format": "standard-user-graphics-folder",
            "entries": manifest_entries,
        }
        (pack_dir / "facestudio-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        (pack_dir / "INSTALL.txt").write_text(self.installation_guide(safe_name), encoding="utf-8")
        return {"pack_dir": pack_dir, "count": copied}

    def _write_config(self, path: Path, mappings: list[tuple[str, str]]) -> None:
        root = ET.Element("record")
        ET.SubElement(root, "boolean", {"id": "preload", "value": "false"})
        ET.SubElement(root, "boolean", {"id": "amap", "value": "false"})
        list_node = ET.SubElement(root, "list", {"id": "maps"})
        for unique_id, file_path in sorted(mappings, key=lambda item: int(item[0])):
            ET.SubElement(list_node, "record", {
                "from": file_path,
                "to": f"graphics/pictures/person/{unique_id}/portrait",
            })
        tree = ET.ElementTree(root)
        ET.indent(tree, space="  ")
        tree.write(path, encoding="utf-8", xml_declaration=True)

    def installation_guide(self, pack_name: str) -> str:
        return (
            f"FM FaceStudio graphics pack: {pack_name}\n\n"
            "1. Close Football Manager.\n"
            "2. Copy this folder into your Football Manager user graphics folder.\n"
            "3. Launch the game and open Preferences.\n"
            "4. Clear the skin cache and reload the skin using the game's available interface options.\n\n"
            "This pack contains standard PNG images and an XML mapping file. It does not modify the game database "
            "or any proprietary archive. Unique IDs must be supplied and checked by the user.\n"
        )

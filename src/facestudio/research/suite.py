from __future__ import annotations

import html
import json
import shutil
import zipfile
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path


class ResearchSuiteService:
    """Cross-library statistics, search, integrity, backup and reporting."""

    STORE_NAMES = (
        "face-library.json",
        "descriptor-presets.json",
        "descriptor-comparison-history.json",
        "facestudio-settings.json",
    )

    def __init__(self, data_dir: Path, face_store, preset_store) -> None:
        self.data_dir = data_dir
        self.face_store = face_store
        self.preset_store = preset_store
        self.backup_dir = data_dir / "backups"
        self.report_dir = data_dir / "reports"

    def statistics(self) -> dict:
        faces = self.face_store.load()
        presets = self.preset_store.load()
        history = self.preset_store.load_history()
        confidence = [item.confidence for item in faces]
        shapes = Counter(item.face_shape or "undetermined" for item in faces)
        collections = Counter(item.collection or "Unsorted" for item in faces)
        collections.update(item.collection or "Unsorted" for item in presets)
        tags = Counter(tag for item in [*faces, *presets] for tag in item.tags)
        return {
            "faces": len(faces),
            "presets": len(presets),
            "comparisons": len(history),
            "favourites": sum(item.favourite for item in faces) + sum(item.favourite for item in presets),
            "average_confidence": sum(confidence) / len(confidence) if confidence else 0.0,
            "face_shapes": dict(shapes.most_common()),
            "collections": dict(collections.most_common()),
            "tags": dict(tags.most_common(12)),
        }

    def global_search(self, query: str) -> list[dict]:
        needle = query.strip().casefold()
        if not needle:
            return []
        results: list[dict] = []
        for item in self.face_store.load():
            haystack = " ".join([item.name, item.face_shape, item.collection, item.notes, *item.tags]).casefold()
            if needle in haystack:
                results.append({"type": "Face", "name": item.name, "collection": item.collection, "detail": item.face_shape})
        for item in self.preset_store.load():
            shape = str(item.descriptor.get("face_shape", "undetermined"))
            haystack = " ".join([item.name, shape, item.collection, item.notes, *item.tags]).casefold()
            if needle in haystack:
                results.append({"type": "Preset", "name": item.name, "collection": item.collection, "detail": shape})
        return results

    def integrity_report(self) -> list[dict]:
        issues: list[dict] = []
        seen_faces: set[str] = set()
        for item in self.face_store.load():
            key = item.name.strip().casefold()
            if key and key in seen_faces:
                issues.append({"severity": "Warning", "item": item.name, "issue": "Duplicate face name"})
            seen_faces.add(key)
            for label, value in (("project", item.project_path), ("source", item.source_photo), ("preview", item.preview_path), ("analysis", item.analysis_path)):
                if value and not Path(value).exists():
                    issues.append({"severity": "Missing", "item": item.name, "issue": f"Missing {label}: {value}"})
        seen_presets: set[str] = set()
        for item in self.preset_store.load():
            key = item.name.strip().casefold()
            if key and key in seen_presets:
                issues.append({"severity": "Warning", "item": item.name, "issue": "Duplicate preset name"})
            seen_presets.add(key)
            if not item.descriptor:
                issues.append({"severity": "Invalid", "item": item.name, "issue": "Preset has no descriptor values"})
        for name in self.STORE_NAMES:
            path = self.data_dir / name
            if path.exists():
                try:
                    json.loads(path.read_text(encoding="utf-8"))
                except (OSError, ValueError, json.JSONDecodeError):
                    issues.append({"severity": "Invalid", "item": name, "issue": "JSON store cannot be read"})
        return issues

    def create_backup(self, destination: Path | None = None) -> Path:
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        target = destination or self.backup_dir / f"facestudio-backup-{stamp}.zip"
        target.parent.mkdir(parents=True, exist_ok=True)
        manifest = {"format": "facestudio-backup", "schema_version": 1, "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("manifest.json", json.dumps(manifest, indent=2))
            for name in self.STORE_NAMES:
                path = self.data_dir / name
                if path.exists():
                    archive.write(path, arcname=name)
        return target

    def restore_backup(self, source: Path) -> None:
        with zipfile.ZipFile(source, "r") as archive:
            manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
            if manifest.get("format") != "facestudio-backup":
                raise ValueError("This archive is not a FaceStudio backup.")
            allowed = set(self.STORE_NAMES)
            for member in archive.namelist():
                if member in allowed:
                    content = archive.read(member)
                    json.loads(content.decode("utf-8"))
                    (self.data_dir / member).write_bytes(content)

    def export_html_report(self, destination: Path, title: str = "FM FaceStudio Research Report") -> Path:
        stats = self.statistics()
        issues = self.integrity_report()
        faces = self.face_store.load()
        presets = self.preset_store.load()
        rows = "".join(
            f"<tr><td>{html.escape(item.name)}</td><td>{html.escape(item.face_shape)}</td><td>{item.confidence:.1%}</td><td>{html.escape(item.collection)}</td></tr>"
            for item in faces
        ) or "<tr><td colspan='4'>No faces in the library.</td></tr>"
        preset_rows = "".join(
            f"<tr><td>{html.escape(item.name)}</td><td>{html.escape(str(item.descriptor.get('face_shape', 'undetermined')))}</td><td>{item.confidence:.1%}</td><td>{html.escape(item.collection)}</td></tr>"
            for item in presets
        ) or "<tr><td colspan='4'>No descriptor presets.</td></tr>"
        issue_rows = "".join(
            f"<li><strong>{html.escape(item['severity'])}</strong> — {html.escape(item['item'])}: {html.escape(item['issue'])}</li>"
            for item in issues
        ) or "<li>No integrity issues detected.</li>"
        document = f"""<!doctype html><html><head><meta charset='utf-8'><title>{html.escape(title)}</title>
<style>body{{font-family:system-ui;margin:40px;max-width:1100px}}table{{border-collapse:collapse;width:100%;margin-bottom:28px}}th,td{{border:1px solid #bbb;padding:8px;text-align:left}}.cards{{display:flex;gap:12px;flex-wrap:wrap}}.card{{border:1px solid #bbb;border-radius:8px;padding:14px;min-width:150px}}</style></head><body>
<h1>{html.escape(title)}</h1><p>Generated {datetime.now(timezone.utc).isoformat(timespec='seconds')} UTC from transparent FaceStudio research metadata.</p>
<div class='cards'><div class='card'><b>Faces</b><br>{stats['faces']}</div><div class='card'><b>Presets</b><br>{stats['presets']}</div><div class='card'><b>Comparisons</b><br>{stats['comparisons']}</div><div class='card'><b>Average confidence</b><br>{stats['average_confidence']:.1%}</div></div>
<h2>Face Library</h2><table><tr><th>Name</th><th>Shape</th><th>Confidence</th><th>Collection</th></tr>{rows}</table>
<h2>Descriptor Presets</h2><table><tr><th>Name</th><th>Shape</th><th>Confidence</th><th>Collection</th></tr>{preset_rows}</table>
<h2>Integrity</h2><ul>{issue_rows}</ul>
<p><small>No proprietary Football Manager mesh data or generated heads are included.</small></p></body></html>"""
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(document, encoding="utf-8")
        return destination

    def rename_collection(self, old_name: str, new_name: str) -> int:
        changed = 0
        faces = self.face_store.load()
        for item in faces:
            if item.collection == old_name:
                item.collection = new_name
                changed += 1
        self.face_store.save(faces)
        presets = self.preset_store.load()
        for item in presets:
            if item.collection == old_name:
                item.collection = new_name
                changed += 1
        self.preset_store.save(presets)
        return changed

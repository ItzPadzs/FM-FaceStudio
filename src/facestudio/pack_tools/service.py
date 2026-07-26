from __future__ import annotations

import json
import os
import shutil
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass(slots=True)
class PackValidationReport:
    pack_dir: str
    valid: bool
    mapping_count: int = 0
    image_count: int = 0
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class PackTestInstallService:
    """Validates and safely copies standard FaceStudio graphics packs."""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.history_path = data_dir / "pack-install-history.json"

    def suggested_graphics_dirs(self) -> list[Path]:
        home = Path.home()
        candidates = [
            home / "Documents" / "Sports Interactive" / "Football Manager 2026" / "graphics",
            home / "Documents" / "Sports Interactive" / "Football Manager 2025" / "graphics",
            home / "Library" / "Application Support" / "Sports Interactive" / "Football Manager 2026" / "graphics",
            home / ".local" / "share" / "Sports Interactive" / "Football Manager 2026" / "graphics",
        ]
        documents = os.environ.get("USERPROFILE")
        if documents:
            candidates.insert(0, Path(documents) / "Documents" / "Sports Interactive" / "Football Manager 2026" / "graphics")
        unique: list[Path] = []
        for candidate in candidates:
            if candidate not in unique:
                unique.append(candidate)
        return unique

    def validate_pack(self, pack_dir: Path) -> PackValidationReport:
        issues: list[str] = []
        warnings: list[str] = []
        config_path = pack_dir / "config.xml"
        faces_dir = pack_dir / "faces"
        if not pack_dir.is_dir():
            return PackValidationReport(str(pack_dir), False, issues=["Pack folder does not exist."])
        if not config_path.is_file():
            issues.append("config.xml is missing.")
        if not faces_dir.is_dir():
            issues.append("faces folder is missing.")

        mappings: list[tuple[str, str]] = []
        if config_path.is_file():
            try:
                root = ET.parse(config_path).getroot()
                for node in root.findall(".//record"):
                    source = node.attrib.get("from", "")
                    target = node.attrib.get("to", "")
                    if source or target:
                        mappings.append((source, target))
            except ET.ParseError as exc:
                issues.append(f"config.xml is not valid XML: {exc}")

        seen_targets: set[str] = set()
        for source, target in mappings:
            if not source.startswith("faces/"):
                warnings.append(f"Unexpected source mapping: {source}")
            if not target.startswith("graphics/pictures/person/") or not target.endswith("/portrait"):
                issues.append(f"Unexpected portrait target: {target}")
            if target in seen_targets:
                issues.append(f"Duplicate target mapping: {target}")
            seen_targets.add(target)
            image_path = pack_dir / f"{source}.png"
            if not image_path.is_file():
                issues.append(f"Mapped image is missing: {image_path.relative_to(pack_dir)}")

        images = list(faces_dir.glob("*.png")) if faces_dir.is_dir() else []
        mapped_sources = {f"{source}.png" for source, _ in mappings}
        for image in images:
            relative = image.relative_to(pack_dir).as_posix()
            if relative not in mapped_sources:
                warnings.append(f"Unmapped image: {relative}")
        if not mappings:
            issues.append("No portrait mappings were found.")
        if not images:
            issues.append("No PNG portraits were found.")

        manifest_path = pack_dir / "facestudio-manifest.json"
        if not manifest_path.is_file():
            warnings.append("FaceStudio manifest is missing; rollback metadata will be limited.")
        else:
            try:
                json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, ValueError, json.JSONDecodeError):
                warnings.append("FaceStudio manifest could not be read.")

        return PackValidationReport(
            pack_dir=str(pack_dir),
            valid=not issues,
            mapping_count=len(mappings),
            image_count=len(images),
            issues=issues,
            warnings=warnings,
        )

    def dry_run(self, pack_dir: Path, graphics_dir: Path) -> list[str]:
        report = self.validate_pack(pack_dir)
        if not report.valid:
            return ["Installation blocked by validation errors.", *report.issues]
        target = graphics_dir / pack_dir.name
        actions = [f"Create graphics folder if needed: {graphics_dir}"]
        if target.exists():
            actions.append(f"Back up existing pack: {target}")
            actions.append(f"Replace existing pack: {target}")
        else:
            actions.append(f"Copy pack to: {target}")
        actions.append(f"Verify {report.mapping_count} XML mappings and {report.image_count} PNG portraits after copying.")
        return actions

    def install(self, pack_dir: Path, graphics_dir: Path) -> dict[str, str | int]:
        report = self.validate_pack(pack_dir)
        if not report.valid:
            raise ValueError("Pack validation failed. Fix all errors before installation.")
        graphics_dir.mkdir(parents=True, exist_ok=True)
        target = graphics_dir / pack_dir.name
        backup = ""
        if target.exists():
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            backup_path = graphics_dir / f"{pack_dir.name}.facestudio-backup-{stamp}"
            shutil.move(str(target), str(backup_path))
            backup = str(backup_path)
        try:
            shutil.copytree(pack_dir, target)
        except Exception:
            if backup and Path(backup).exists() and not target.exists():
                shutil.move(backup, target)
            raise

        verify = self.validate_pack(target)
        if not verify.valid:
            shutil.rmtree(target, ignore_errors=True)
            if backup and Path(backup).exists():
                shutil.move(backup, target)
            raise ValueError("Installed copy failed verification and was rolled back.")

        record = {
            "installed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "source": str(pack_dir),
            "target": str(target),
            "backup": backup,
            "mapping_count": verify.mapping_count,
            "image_count": verify.image_count,
        }
        self._append_history(record)
        (target / "facestudio-install.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
        return record

    def verify_installed(self, target: Path) -> PackValidationReport:
        return self.validate_pack(target)

    def _append_history(self, record: dict[str, str | int]) -> None:
        history: list[dict[str, str | int]] = []
        if self.history_path.exists():
            try:
                payload = json.loads(self.history_path.read_text(encoding="utf-8"))
                if isinstance(payload, list):
                    history = [item for item in payload if isinstance(item, dict)]
            except (OSError, ValueError, json.JSONDecodeError):
                history = []
        history.insert(0, record)
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        self.history_path.write_text(json.dumps(history[:100], indent=2), encoding="utf-8")

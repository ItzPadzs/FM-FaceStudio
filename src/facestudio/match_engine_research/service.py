from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class AssetRecord:
    path: str
    extension: str
    size_bytes: int
    sha256: str
    header_hex: str
    category: str


@dataclass(frozen=True)
class ScanReport:
    root: str
    scanned_at: str
    records: tuple[AssetRecord, ...]
    skipped: tuple[str, ...]

    @property
    def file_count(self) -> int:
        return len(self.records)


class MatchEngineResearchService:
    """Read-only inventory tooling for user-selected loose files.

    This service deliberately does not unpack, decrypt, alter or write into
    Football Manager installations. It records basic evidence that can be
    compared between controlled experiments.
    """

    MAX_HASH_BYTES = 256 * 1024 * 1024
    HEADER_BYTES = 32

    CATEGORY_EXTENSIONS = {
        "image": {".png", ".jpg", ".jpeg", ".bmp", ".tga", ".dds", ".webp"},
        "model": {".obj", ".fbx", ".dae", ".gltf", ".glb", ".mesh"},
        "material": {".mtl", ".material", ".mat"},
        "data": {".xml", ".json", ".txt", ".csv", ".bin", ".dat"},
        "archive": {".fmf", ".zip", ".7z", ".rar"},
    }

    def scan(self, root: Path) -> ScanReport:
        root = root.expanduser().resolve()
        if not root.is_dir():
            raise ValueError("Select a folder that exists.")

        records: list[AssetRecord] = []
        skipped: list[str] = []
        for path in sorted(item for item in root.rglob("*") if item.is_file()):
            relative = path.relative_to(root).as_posix()
            try:
                size = path.stat().st_size
                if size > self.MAX_HASH_BYTES:
                    skipped.append(f"{relative}: larger than the 256 MB safety limit")
                    continue
                content = path.read_bytes()
            except OSError as exc:
                skipped.append(f"{relative}: {exc}")
                continue

            extension = path.suffix.lower()
            records.append(
                AssetRecord(
                    path=relative,
                    extension=extension or "(none)",
                    size_bytes=size,
                    sha256=hashlib.sha256(content).hexdigest(),
                    header_hex=content[: self.HEADER_BYTES].hex(" "),
                    category=self.classify(extension),
                )
            )

        return ScanReport(
            root=str(root),
            scanned_at=datetime.now(timezone.utc).isoformat(),
            records=tuple(records),
            skipped=tuple(skipped),
        )

    def classify(self, extension: str) -> str:
        for category, extensions in self.CATEGORY_EXTENSIONS.items():
            if extension in extensions:
                return category
        return "unknown"

    def export_report(self, report: ScanReport, destination: Path) -> Path:
        destination = destination.expanduser()
        destination.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema": "facestudio-match-engine-research-v1",
            "scope": "Read-only inventory of user-selected loose files; no archive decoding.",
            "root": report.root,
            "scanned_at": report.scanned_at,
            "file_count": report.file_count,
            "records": [asdict(record) for record in report.records],
            "skipped": list(report.skipped),
        }
        destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return destination

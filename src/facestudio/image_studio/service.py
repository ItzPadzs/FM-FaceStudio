from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QImage, QImageReader, QTransform

SUPPORTED_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}


@dataclass(slots=True)
class ImageRecord:
    id: str
    source_path: str
    name: str
    width: int
    height: int
    file_size: int
    imported_at: str
    crop_mode: str = "Original"
    rotation: int = 0
    brightness: int = 0
    contrast: int = 0
    saturation: int = 0
    background: str = "Original"
    output_size: int = 250
    output_format: str = "PNG"
    quality_score: int = 0
    issues: list[str] = field(default_factory=list)
    exported_path: str = ""
    history: list[str] = field(default_factory=lambda: ["Imported"])

    @classmethod
    def from_dict(cls, payload: dict) -> "ImageRecord":
        return cls(
            id=str(payload.get("id") or uuid4()),
            source_path=str(payload.get("source_path", "")),
            name=str(payload.get("name", "Untitled image")),
            width=int(payload.get("width", 0)),
            height=int(payload.get("height", 0)),
            file_size=int(payload.get("file_size", 0)),
            imported_at=str(payload.get("imported_at", "")),
            crop_mode=str(payload.get("crop_mode", "Original")),
            rotation=int(payload.get("rotation", 0)),
            brightness=int(payload.get("brightness", 0)),
            contrast=int(payload.get("contrast", 0)),
            saturation=int(payload.get("saturation", 0)),
            background=str(payload.get("background", "Original")),
            output_size=int(payload.get("output_size", 250)),
            output_format=str(payload.get("output_format", "PNG")),
            quality_score=int(payload.get("quality_score", 0)),
            issues=[str(value) for value in payload.get("issues", [])],
            exported_path=str(payload.get("exported_path", "")),
            history=[str(value) for value in payload.get("history", ["Imported"])],
        )


class ImageStudioService:
    """Local, non-destructive image preparation using Qt image primitives."""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.store_path = data_dir / "image-studio-library.json"
        self.export_dir = data_dir / "image-studio-exports"

    def load(self) -> list[ImageRecord]:
        if not self.store_path.exists():
            return []
        try:
            payload = json.loads(self.store_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError):
            return []
        return [ImageRecord.from_dict(item) for item in payload if isinstance(item, dict)]

    def save(self, records: list[ImageRecord]) -> None:
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.store_path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps([asdict(item) for item in records], indent=2), encoding="utf-8")
        temporary.replace(self.store_path)

    def import_paths(self, paths: list[Path]) -> tuple[int, list[str]]:
        records = self.load()
        known = {Path(item.source_path).resolve() for item in records if item.source_path}
        imported = 0
        errors: list[str] = []
        candidates: list[Path] = []
        for path in paths:
            if path.is_dir():
                candidates.extend(item for item in path.rglob("*") if item.suffix.lower() in SUPPORTED_SUFFIXES)
            elif path.suffix.lower() in SUPPORTED_SUFFIXES:
                candidates.append(path)
        for path in candidates:
            resolved = path.resolve()
            if resolved in known:
                continue
            reader = QImageReader(str(path))
            size = reader.size()
            if not size.isValid():
                errors.append(f"Could not read {path.name}")
                continue
            issues, score = self.inspect(path, size.width(), size.height())
            records.insert(0, ImageRecord(
                id=str(uuid4()),
                source_path=str(resolved),
                name=path.stem,
                width=size.width(),
                height=size.height(),
                file_size=path.stat().st_size,
                imported_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                quality_score=score,
                issues=issues,
            ))
            known.add(resolved)
            imported += 1
        self.save(records)
        return imported, errors

    def inspect(self, path: Path, width: int, height: int) -> tuple[list[str], int]:
        issues: list[str] = []
        score = 100
        if min(width, height) < 180:
            issues.append("Low resolution")
            score -= 35
        elif min(width, height) < 512:
            issues.append("Below HD working size")
            score -= 12
        ratio = width / max(1, height)
        if ratio > 2.2 or ratio < 0.45:
            issues.append("Unusual orientation")
            score -= 12
        if path.stat().st_size < 20_000:
            issues.append("Possible heavy compression")
            score -= 15
        if width != height:
            issues.append("Requires portrait crop")
            score -= 5
        return issues, max(0, score)

    def update(self, record: ImageRecord) -> None:
        records = self.load()
        for index, current in enumerate(records):
            if current.id == record.id:
                records[index] = record
                break
        self.save(records)

    def remove(self, record_id: str) -> None:
        self.save([item for item in self.load() if item.id != record_id])

    def render(self, record: ImageRecord) -> QImage:
        image = QImage(record.source_path)
        if image.isNull():
            return image
        image = image.convertToFormat(QImage.Format.Format_ARGB32)
        if record.rotation:
            image = image.transformed(QTransform().rotate(record.rotation), Qt.TransformationMode.SmoothTransformation)
        if record.crop_mode != "Original":
            side = min(image.width(), image.height())
            x = (image.width() - side) // 2
            y = max(0, int((image.height() - side) * 0.35))
            image = image.copy(QRect(x, y, side, side))
        image = self._adjust(image, record.brightness, record.contrast, record.saturation)
        if record.background != "Original":
            colour = {"White": QColor("white"), "Grey": QColor("#808080"), "Black": QColor("black")}.get(record.background)
            if colour is not None:
                canvas = QImage(image.size(), QImage.Format.Format_ARGB32)
                canvas.fill(colour)
                from PySide6.QtGui import QPainter
                painter = QPainter(canvas)
                painter.drawImage(0, 0, image)
                painter.end()
                image = canvas
        return image

    def _adjust(self, image: QImage, brightness: int, contrast: int, saturation: int) -> QImage:
        if brightness == 0 and contrast == 0 and saturation == 0:
            return image
        result = image.copy()
        contrast_factor = (259 * (contrast + 255)) / max(1, 255 * (259 - contrast))
        saturation_factor = 1.0 + saturation / 100.0
        for y in range(result.height()):
            for x in range(result.width()):
                colour = result.pixelColor(x, y)
                red = contrast_factor * (colour.red() - 128) + 128 + brightness
                green = contrast_factor * (colour.green() - 128) + 128 + brightness
                blue = contrast_factor * (colour.blue() - 128) + 128 + brightness
                grey = 0.299 * red + 0.587 * green + 0.114 * blue
                red = grey + (red - grey) * saturation_factor
                green = grey + (green - grey) * saturation_factor
                blue = grey + (blue - grey) * saturation_factor
                colour.setRed(max(0, min(255, int(red))))
                colour.setGreen(max(0, min(255, int(green))))
                colour.setBlue(max(0, min(255, int(blue))))
                result.setPixelColor(x, y, colour)
        return result

    def export(self, record: ImageRecord, destination: Path | None = None) -> Path:
        image = self.render(record)
        if image.isNull():
            raise ValueError("The source image could not be loaded.")
        image = image.scaled(record.output_size, record.output_size, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
        image = image.copy(0, 0, record.output_size, record.output_size)
        suffix = record.output_format.lower().replace("jpeg", "jpg")
        target_dir = destination or self.export_dir
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / f"{record.name}.{suffix}"
        if not image.save(str(target), record.output_format):
            raise ValueError("Qt could not encode the selected output format.")
        sidecar = target.with_suffix(target.suffix + ".json")
        sidecar.write_text(json.dumps(asdict(record), indent=2), encoding="utf-8")
        record.exported_path = str(target)
        record.history.append(f"Exported {record.output_size}x{record.output_size} {record.output_format}")
        self.update(record)
        return target

    def batch_export(self, records: list[ImageRecord], destination: Path) -> tuple[int, list[str]]:
        completed = 0
        errors: list[str] = []
        for record in records:
            try:
                self.export(record, destination)
                completed += 1
            except (OSError, ValueError) as exc:
                errors.append(f"{record.name}: {exc}")
        return completed, errors

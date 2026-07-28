from __future__ import annotations

from dataclasses import asdict, dataclass
import csv
import json
import math
from pathlib import Path
from typing import Iterable

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QImage, QImageReader

DONOR_INDEX_FORMAT = "facestudio-donor-asset-index-v1"
SUPPORTED_IMAGES = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


@dataclass(frozen=True)
class DonorAsset:
    donor_id: str
    name: str
    diffuse: str | None = None
    face_crop: str | None = None
    geometry: str | None = None
    hair: str | None = None
    beard: str | None = None
    eyes: str | None = None
    skin_tone: tuple[int, int, int] | None = None
    descriptor: tuple[float, ...] = ()


@dataclass(frozen=True)
class DonorMatch:
    donor_id: str
    name: str
    score: float
    diffuse: str
    face_crop: str | None


class DonorAssetIndexer:
    """Index real donor assets without copying the source pack.

    Numeric filename stems are treated as donor identifiers. Optional CSV/JSON metadata
    may map those identifiers to names. Asset type is inferred conservatively from path
    names; ambiguous images are treated as diffuse head textures.
    """

    def build(
        self,
        roots: Iterable[Path],
        output_directory: Path,
        *,
        names_file: Path | None = None,
        write_thumbnails: bool = True,
    ) -> Path:
        output_directory = Path(output_directory).expanduser().resolve()
        output_directory.mkdir(parents=True, exist_ok=True)
        thumbnail_directory = output_directory / "face-thumbnails"
        if write_thumbnails:
            thumbnail_directory.mkdir(parents=True, exist_ok=True)

        names = self._load_names(names_file)
        records: dict[str, dict[str, object]] = {}
        scanned_roots: list[str] = []

        for raw_root in roots:
            root = Path(raw_root).expanduser().resolve()
            if not root.is_dir():
                continue
            scanned_roots.append(str(root))
            for path in sorted(p for p in root.rglob("*") if p.is_file()):
                donor_id = self._donor_id(path)
                if not donor_id:
                    continue
                kind = self._asset_kind(path)
                record = records.setdefault(
                    donor_id,
                    {
                        "donor_id": donor_id,
                        "name": names.get(donor_id, donor_id),
                        "diffuse": None,
                        "face_crop": None,
                        "geometry": None,
                        "hair": None,
                        "beard": None,
                        "eyes": None,
                        "skin_tone": None,
                        "descriptor": [],
                    },
                )
                if kind == "geometry":
                    record["geometry"] = str(path)
                elif kind in {"hair", "beard", "eyes"}:
                    record[kind] = str(path)
                elif path.suffix.lower() in SUPPORTED_IMAGES:
                    record["diffuse"] = str(path)

        donors: list[dict[str, object]] = []
        for donor_id in sorted(records, key=lambda value: (not value.isdigit(), int(value) if value.isdigit() else value)):
            record = records[donor_id]
            diffuse_value = record.get("diffuse")
            if diffuse_value:
                diffuse = Path(str(diffuse_value))
                image = self._read_image(diffuse)
                crop = self.extract_face_crop(image)
                record["skin_tone"] = list(self._average_colour(crop))
                record["descriptor"] = list(self._descriptor(crop))
                if write_thumbnails:
                    thumbnail = thumbnail_directory / f"{donor_id}.png"
                    crop.scaled(192, 192, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation).save(str(thumbnail), "PNG")
                    record["face_crop"] = str(thumbnail)
            donors.append(record)

        index_path = output_directory / "donor-asset-index.json"
        index_path.write_text(
            json.dumps(
                {
                    "format": DONOR_INDEX_FORMAT,
                    "roots": scanned_roots,
                    "count": len(donors),
                    "donors": donors,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return index_path

    @staticmethod
    def extract_face_crop(image: QImage) -> QImage:
        """Extract the repeatable face window visible in FM diffuse atlases."""
        if image.isNull():
            raise ValueError("Cannot crop an empty image")
        width, height = image.width(), image.height()
        left = int(width * 0.25)
        top = int(height * 0.16)
        crop_width = max(1, int(width * 0.50))
        crop_height = max(1, int(height * 0.50))
        return image.copy(QRect(left, top, min(crop_width, width - left), min(crop_height, height - top)))

    @staticmethod
    def _donor_id(path: Path) -> str | None:
        stem = path.stem
        if stem.isdigit():
            return stem
        for part in reversed(path.parts):
            if part.isdigit():
                return part
        return None

    @staticmethod
    def _asset_kind(path: Path) -> str:
        label = "/".join(part.lower() for part in path.parts)
        suffix = path.suffix.lower()
        if suffix in {".skin", ".mesh", ".obj", ".fbx", ".gltf", ".glb"}:
            return "geometry"
        if "beard" in label or "facial_hair" in label:
            return "beard"
        if "eye" in label:
            return "eyes"
        if "hair" in label:
            return "hair"
        return "diffuse"

    @staticmethod
    def _read_image(path: Path) -> QImage:
        reader = QImageReader(str(path))
        reader.setAutoTransform(True)
        image = reader.read()
        if image.isNull():
            raise ValueError(f"Could not read donor image {path}: {reader.errorString()}")
        return image.convertToFormat(QImage.Format.Format_RGB32)

    @staticmethod
    def _average_colour(image: QImage) -> tuple[int, int, int]:
        sample = image.scaled(16, 16, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
        r = g = b = 0
        count = sample.width() * sample.height()
        for y in range(sample.height()):
            for x in range(sample.width()):
                colour = sample.pixelColor(x, y)
                r += colour.red(); g += colour.green(); b += colour.blue()
        return (r // count, g // count, b // count)

    @staticmethod
    def _descriptor(image: QImage) -> tuple[float, ...]:
        sample = image.scaled(8, 8, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
        values: list[float] = []
        for y in range(sample.height()):
            for x in range(sample.width()):
                colour = sample.pixelColor(x, y)
                values.extend((colour.redF(), colour.greenF(), colour.blueF()))
        norm = math.sqrt(sum(value * value for value in values)) or 1.0
        return tuple(value / norm for value in values)

    @staticmethod
    def _load_names(names_file: Path | None) -> dict[str, str]:
        if names_file is None:
            return {}
        path = Path(names_file).expanduser().resolve()
        if not path.is_file():
            raise ValueError(f"Donor name map not found: {path}")
        if path.suffix.lower() == ".json":
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                return {str(key): str(value) for key, value in payload.items()}
            raise ValueError("Donor JSON name map must be an object of id: name values")
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = csv.DictReader(handle)
            result: dict[str, str] = {}
            for row in rows:
                donor_id = str(row.get("id") or row.get("uid") or row.get("donor_id") or "").strip()
                name = str(row.get("name") or row.get("player_name") or "").strip()
                if donor_id and name:
                    result[donor_id] = name
            return result


class DonorMatcher:
    """Rank indexed donor diffuse textures using a deterministic visual descriptor."""

    def __init__(self, index_path: Path) -> None:
        payload = json.loads(Path(index_path).read_text(encoding="utf-8"))
        if payload.get("format") != DONOR_INDEX_FORMAT:
            raise ValueError("Unsupported donor index format")
        self.donors = list(payload.get("donors", []))

    def rank(self, portrait: Path, *, limit: int = 12) -> list[DonorMatch]:
        image = DonorAssetIndexer._read_image(Path(portrait))
        portrait_crop = self._portrait_crop(image)
        query = DonorAssetIndexer._descriptor(portrait_crop)
        matches: list[DonorMatch] = []
        for donor in self.donors:
            descriptor = tuple(float(value) for value in donor.get("descriptor", []))
            diffuse = donor.get("diffuse")
            if not descriptor or not diffuse or len(descriptor) != len(query):
                continue
            similarity = sum(a * b for a, b in zip(query, descriptor))
            score = max(0.0, min(100.0, similarity * 100.0))
            matches.append(
                DonorMatch(
                    donor_id=str(donor["donor_id"]),
                    name=str(donor.get("name") or donor["donor_id"]),
                    score=round(score, 2),
                    diffuse=str(diffuse),
                    face_crop=str(donor.get("face_crop")) if donor.get("face_crop") else None,
                )
            )
        matches.sort(key=lambda match: (-match.score, match.name.casefold(), match.donor_id))
        return matches[: max(1, int(limit))]

    @staticmethod
    def _portrait_crop(image: QImage) -> QImage:
        width, height = image.width(), image.height()
        side = max(1, min(width, height))
        left = max(0, (width - side) // 2)
        top = max(0, int((height - side) * 0.35))
        top = min(top, height - side)
        return image.copy(QRect(left, top, side, side))

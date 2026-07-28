from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
DATASET_FORMAT = "facestudio-portrait-uv-pairs-v1"


@dataclass(frozen=True)
class TrainingPair:
    identity: str
    portrait: str
    uv_texture: str


@dataclass(frozen=True)
class DatasetIndex:
    format: str
    portrait_root: str
    uv_root: str
    pairs: tuple[TrainingPair, ...]
    missing_portraits: tuple[str, ...]
    missing_uv_textures: tuple[str, ...]


class PairedDatasetBuilder:
    """Build a deterministic portrait-to-UV training index.

    Files are paired by filename stem. For example, ``12345.jpg`` is matched with
    ``12345.png``. The builder does not infer identities or fabricate missing pairs.
    """

    def build(self, portrait_root: Path, uv_root: Path, output: Path) -> DatasetIndex:
        portrait_root = Path(portrait_root).expanduser().resolve()
        uv_root = Path(uv_root).expanduser().resolve()
        output = Path(output).expanduser().resolve()
        if not portrait_root.is_dir():
            raise ValueError(f"Portrait folder not found: {portrait_root}")
        if not uv_root.is_dir():
            raise ValueError(f"UV texture folder not found: {uv_root}")

        portraits = self._index_images(portrait_root)
        textures = self._index_images(uv_root)
        identities = sorted(set(portraits) | set(textures))
        pairs = tuple(
            TrainingPair(identity, str(portraits[identity]), str(textures[identity]))
            for identity in identities
            if identity in portraits and identity in textures
        )
        index = DatasetIndex(
            format=DATASET_FORMAT,
            portrait_root=str(portrait_root),
            uv_root=str(uv_root),
            pairs=pairs,
            missing_portraits=tuple(identity for identity in identities if identity not in portraits),
            missing_uv_textures=tuple(identity for identity in identities if identity not in textures),
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        payload = asdict(index)
        payload["pair_count"] = len(pairs)
        output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return index

    @staticmethod
    def _index_images(root: Path) -> dict[str, Path]:
        result: dict[str, Path] = {}
        for path in sorted(root.rglob("*")):
            if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES:
                result.setdefault(path.stem, path.resolve())
        return result

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QRectF

from facestudio.ai.skin_transfer.masks import ProtectedRegions


@dataclass(frozen=True)
class MaskProfile:
    profile_id: str
    display_name: str
    regions: ProtectedRegions
    source: Path


def _rect(value: object, field: str) -> QRectF:
    if not isinstance(value, list) or len(value) != 4:
        raise ValueError(f"{field} must contain four normalised numbers")
    numbers = [float(item) for item in value]
    if any(item < 0.0 or item > 1.0 for item in numbers):
        raise ValueError(f"{field} values must be between 0 and 1")
    x, y, width, height = numbers
    if width <= 0.0 or height <= 0.0 or x + width > 1.0 or y + height > 1.0:
        raise ValueError(f"{field} rectangle must fit inside the UV canvas")
    return QRectF(x, y, width, height)


def load_mask_profile(path: Path) -> MaskProfile:
    source = path.expanduser().resolve()
    data = json.loads(source.read_text(encoding="utf-8"))
    profile_id = str(data.get("id", "")).strip()
    display_name = str(data.get("name", "")).strip()
    regions = data.get("regions")
    if not profile_id or not display_name or not isinstance(regions, dict):
        raise ValueError("Mask profile requires id, name and regions")

    eyes = regions.get("eyes")
    ears = regions.get("ears")
    if not isinstance(eyes, list) or len(eyes) != 2:
        raise ValueError("regions.eyes must contain left and right rectangles")
    if not isinstance(ears, list) or len(ears) != 2:
        raise ValueError("regions.ears must contain left and right rectangles")

    protected = ProtectedRegions(
        eyes=(_rect(eyes[0], "regions.eyes[0]"), _rect(eyes[1], "regions.eyes[1]")),
        nostrils=_rect(regions.get("nostrils"), "regions.nostrils"),
        mouth=_rect(regions.get("mouth"), "regions.mouth"),
        ears=(_rect(ears[0], "regions.ears[0]"), _rect(ears[1], "regions.ears[1]")),
    )
    return MaskProfile(profile_id, display_name, protected, source)

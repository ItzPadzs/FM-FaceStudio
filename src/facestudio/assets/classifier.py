from __future__ import annotations

from pathlib import Path


def classify_asset(path: Path) -> str:
    """Return a cautious category based only on path and extension.

    This deliberately avoids claiming knowledge of proprietary FM formats.
    Categories can be improved later when formats are formally validated.
    """
    name = path.name.lower()
    parts = {part.lower() for part in path.parts}
    extension = path.suffix.lower()

    if any(token in parts or token in name for token in ("hair", "hairstyle")):
        return "Hair"
    if any(token in parts or token in name for token in ("beard", "facial_hair", "facialhair")):
        return "Facial Hair"
    if any(token in parts or token in name for token in ("head", "face", "faces")):
        return "Head / Face"
    if extension in {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tga", ".dds"}:
        return "Texture / Image"
    if extension in {".skin", ".mesh", ".model", ".obj", ".fbx"}:
        return "Mesh / Model"
    if extension in {".xml", ".json", ".yaml", ".yml", ".cfg", ".ini"}:
        return "Metadata / Config"
    if extension in {".zip", ".rar", ".7z", ".fmf", ".pak", ".bundle"}:
        return "Archive / Bundle"
    if extension:
        return "Other"
    return "No Extension"

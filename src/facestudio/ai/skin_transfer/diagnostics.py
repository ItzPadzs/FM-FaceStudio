from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QImage


def save_diagnostics(output_dir: Path, images: dict[str, QImage]) -> tuple[Path, ...]:
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for name, image in images.items():
        path = output_dir / f"{name}.png"
        if image.isNull() or not image.save(str(path), "PNG"):
            raise RuntimeError(f"Could not save diagnostic image: {path}")
        written.append(path)
    return tuple(written)

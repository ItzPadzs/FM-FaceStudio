from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class BinaryInspection:
    path: Path
    size_bytes: int
    header_hex: str
    printable_header: str


def inspect_binary(path: Path, header_length: int = 128) -> BinaryInspection:
    with path.open("rb") as handle:
        data = handle.read(max(1, header_length))
    return BinaryInspection(
        path=path,
        size_bytes=path.stat().st_size,
        header_hex=" ".join(f"{value:02X}" for value in data),
        printable_header="".join(
            chr(value) if 32 <= value <= 126 else "."
            for value in data
        ),
    )

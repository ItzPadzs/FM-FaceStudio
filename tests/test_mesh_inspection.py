from pathlib import Path

from facestudio.mesh.inspection import inspect_binary


def test_binary_inspection(tmp_path: Path) -> None:
    path = tmp_path / "sample.skin"
    path.write_bytes(b"ABC\x00\xff")
    result = inspect_binary(path)
    assert result.size_bytes == 5
    assert result.header_hex.startswith("41 42 43")
    assert result.printable_header.startswith("ABC")

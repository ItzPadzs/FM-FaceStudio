from pathlib import Path

from facestudio.assets.scanner import AssetScanner


def test_scanner_collects_metadata(tmp_path: Path) -> None:
    (tmp_path / "heads").mkdir()
    (tmp_path / "heads" / "example.skin").write_bytes(b"123")
    (tmp_path / "image.png").write_bytes(b"4567")

    result = AssetScanner().scan(tmp_path)

    assert len(result.records) == 2
    assert {record.relative_path for record in result.records} == {
        "heads/example.skin",
        "image.png",
    }

from pathlib import Path

from facestudio.assets.database import AssetDatabase
from facestudio.assets.models import AssetRecord


def make_record(relative: str, asset_type: str) -> AssetRecord:
    path = Path(relative)
    return AssetRecord(
        path=path,
        relative_path=relative,
        filename=path.name,
        extension=path.suffix,
        asset_type=asset_type,
        size_bytes=123,
        modified_time=1000.0,
    )


def test_replace_and_search(tmp_path: Path) -> None:
    database = AssetDatabase(tmp_path / "assets.sqlite3")
    root = tmp_path / "game"
    database.replace_root(
        root,
        [
            make_record("heads/a.skin", "Head / Face"),
            make_record("hair/b.skin", "Hair"),
        ],
    )

    assert database.total_count() == 2
    assert len(database.search(query="a.skin")) == 1
    assert len(database.search(asset_type="Hair")) == 1


def test_replace_root_removes_old_entries(tmp_path: Path) -> None:
    database = AssetDatabase(tmp_path / "assets.sqlite3")
    root = tmp_path / "game"

    database.replace_root(root, [make_record("one.png", "Texture / Image")])
    database.replace_root(root, [make_record("two.png", "Texture / Image")])

    rows = database.search()
    assert len(rows) == 1
    assert rows[0]["filename"] == "two.png"

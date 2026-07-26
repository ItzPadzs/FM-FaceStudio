from pathlib import Path
from facestudio.assets.index import AssetIndex, AssetRecord


def test_asset_index_clear() -> None:
    index = AssetIndex()
    index._records.append(AssetRecord("head", Path("head.skin"), 123))
    assert len(index.records) == 1
    index.clear()
    assert index.records == ()

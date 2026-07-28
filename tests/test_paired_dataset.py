from pathlib import Path
import json

from facestudio.ai.paired_dataset import DATASET_FORMAT, PairedDatasetBuilder


def test_pairs_images_by_filename_stem(tmp_path: Path) -> None:
    portraits = tmp_path / "portraits"
    textures = tmp_path / "textures"
    portraits.mkdir()
    textures.mkdir()
    (portraits / "100.jpg").write_bytes(b"portrait")
    (portraits / "200.png").write_bytes(b"portrait")
    (textures / "100.png").write_bytes(b"texture")
    (textures / "300.png").write_bytes(b"texture")
    output = tmp_path / "dataset.json"

    index = PairedDatasetBuilder().build(portraits, textures, output)

    assert [pair.identity for pair in index.pairs] == ["100"]
    assert index.missing_portraits == ("300",)
    assert index.missing_uv_textures == ("200",)
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["format"] == DATASET_FORMAT
    assert payload["pair_count"] == 1

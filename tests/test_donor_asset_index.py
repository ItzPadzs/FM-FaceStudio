from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtGui import QColor, QImage

from facestudio.donor_asset_index import DONOR_INDEX_FORMAT, DonorAssetIndexer, DonorMatcher


def _save_image(path: Path, colour: tuple[int, int, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image = QImage(1024, 1024, QImage.Format.Format_RGB32)
    image.fill(QColor(*colour))
    assert image.save(str(path), "PNG")


def test_builds_named_donor_index_and_thumbnails(tmp_path: Path) -> None:
    pack = tmp_path / "pack"
    _save_image(pack / "heads" / "1001.png", (180, 120, 95))
    _save_image(pack / "heads" / "1002.png", (80, 55, 45))
    (pack / "geometry").mkdir(parents=True)
    (pack / "geometry" / "1001.skin").write_bytes(b"not parsed")
    names = tmp_path / "names.json"
    names.write_text(json.dumps({"1001": "Donor One", "1002": "Donor Two"}), encoding="utf-8")

    index_path = DonorAssetIndexer().build([pack], tmp_path / "index", names_file=names)
    payload = json.loads(index_path.read_text(encoding="utf-8"))

    assert payload["format"] == DONOR_INDEX_FORMAT
    assert payload["count"] == 2
    assert payload["donors"][0]["name"] == "Donor One"
    assert Path(payload["donors"][0]["face_crop"]).is_file()
    assert payload["donors"][0]["geometry"].endswith("1001.skin")
    assert len(payload["donors"][0]["descriptor"]) == 192


def test_ranks_visually_closest_donor_first(tmp_path: Path) -> None:
    pack = tmp_path / "pack"
    _save_image(pack / "1001.png", (190, 125, 100))
    _save_image(pack / "1002.png", (55, 40, 35))
    portrait = tmp_path / "portrait.png"
    _save_image(portrait, (188, 123, 98))

    index_path = DonorAssetIndexer().build([pack], tmp_path / "index")
    matches = DonorMatcher(index_path).rank(portrait, limit=2)

    assert [match.donor_id for match in matches] == ["1001", "1002"]
    assert matches[0].score >= matches[1].score


def test_indexes_separate_hair_beard_and_eye_assets(tmp_path: Path) -> None:
    pack = tmp_path / "pack"
    _save_image(pack / "heads" / "2001.png", (130, 90, 70))
    _save_image(pack / "hair" / "2001.png", (20, 15, 10))
    _save_image(pack / "beards" / "2001.png", (25, 18, 12))
    _save_image(pack / "eyes" / "2001.png", (70, 80, 90))

    index_path = DonorAssetIndexer().build([pack], tmp_path / "index", write_thumbnails=False)
    donor = json.loads(index_path.read_text(encoding="utf-8"))["donors"][0]

    assert donor["diffuse"].endswith("heads/2001.png") or donor["diffuse"].endswith("heads\\2001.png")
    assert donor["hair"].endswith("hair/2001.png") or donor["hair"].endswith("hair\\2001.png")
    assert donor["beard"].endswith("beards/2001.png") or donor["beard"].endswith("beards\\2001.png")
    assert donor["eyes"].endswith("eyes/2001.png") or donor["eyes"].endswith("eyes\\2001.png")

from __future__ import annotations

import json
from pathlib import Path

import pytest

from facestudio.match_engine_research.head_explorer import HeadExplorerService
from facestudio.match_engine_research.service import MatchEngineResearchService


def test_scan_records_hash_header_and_category(tmp_path: Path) -> None:
    (tmp_path / "face.png").write_bytes(b"\x89PNG\r\n\x1a\nexample")
    (tmp_path / "model.mesh").write_bytes(b"MESHdata")

    report = MatchEngineResearchService().scan(tmp_path)

    assert report.file_count == 2
    by_name = {record.path: record for record in report.records}
    assert by_name["face.png"].category == "image"
    assert by_name["face.png"].header_hex.startswith("89 50 4e 47")
    assert len(by_name["face.png"].sha256) == 64
    assert by_name["model.mesh"].category == "model"


def test_scan_rejects_missing_folder(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="exists"):
        MatchEngineResearchService().scan(tmp_path / "missing")


def test_export_report_is_transparent_json(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "sample.dat").write_bytes(b"example")

    service = MatchEngineResearchService()
    report = service.scan(source)
    destination = service.export_report(report, tmp_path / "report.json")
    payload = json.loads(destination.read_text(encoding="utf-8"))

    assert payload["schema"] == "facestudio-match-engine-research-v1"
    assert payload["file_count"] == 1
    assert payload["records"][0]["path"] == "sample.dat"
    assert "no archive decoding" in payload["scope"].lower()


def test_head_explorer_groups_player_assets_and_cfg2(tmp_path: Path) -> None:
    (tmp_path / "_players.json").write_text(
        json.dumps({"2000382120": "Chido Obi"}), encoding="utf-8"
    )
    (tmp_path / "2000382120.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    (tmp_path / "2000382120.cfg2").write_text(
        "# chain-skinned donor (auto-converted)\n"
        "eye_l=-0.0312,0.0586,0.0583\n"
        "eye_r=0.0312,0.0586,0.0583\n"
        "eye_s=1.000\n"
        "hair_color=#ffffff\n",
        encoding="utf-8",
    )
    (tmp_path / "2000382120.skin").write_bytes(
        (2410).to_bytes(4, "little") + (13106).to_bytes(4, "little") + b"binary"
    )
    (tmp_path / "2000382120_hair.skin").write_bytes(b"hair")
    (tmp_path / "2000382120_hair2.png").write_bytes(b"png")

    library = HeadExplorerService().load(tmp_path)

    assert len(library.records) == 1
    record = library.records[0]
    assert record.player_id == "2000382120"
    assert record.player_name == "Chido Obi"
    assert record.face_png == "2000382120.png"
    assert record.hair_skin == "2000382120_hair.skin"
    assert record.hair2_png == "2000382120_hair2.png"
    assert record.cfg2_values["eye_s"] == "1.000"
    assert record.cfg2_comments == ("chain-skinned donor (auto-converted)",)
    assert record.skin_summary is not None
    assert record.skin_summary.little_endian_u32[:2] == (2410, 13106)


def test_head_explorer_keeps_unknown_ids_and_missing_players_file(tmp_path: Path) -> None:
    (tmp_path / "123.skin").write_bytes(b"\x01\x00\x00\x00")

    library = HeadExplorerService().load(tmp_path)

    assert library.records[0].player_name == "Unknown player"
    assert any("_players.json" in warning for warning in library.warnings)


def test_head_report_export_is_read_only_evidence(tmp_path: Path) -> None:
    source = tmp_path / "heads"
    source.mkdir()
    (source / "_players.json").write_text('{"42": "Example Player"}', encoding="utf-8")
    (source / "42.cfg2").write_text("eye_s=1.000\n", encoding="utf-8")

    service = HeadExplorerService()
    library = service.load(source)
    destination = service.export_library(library, tmp_path / "head-report.json")
    payload = json.loads(destination.read_text(encoding="utf-8"))

    assert payload["schema"] == "facestudio-fm26-head-library-v1"
    assert payload["record_count"] == 1
    assert payload["records"][0]["player_name"] == "Example Player"
    assert "read-only" in payload["scope"].lower()

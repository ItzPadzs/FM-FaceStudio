from __future__ import annotations

import json
from pathlib import Path

import pytest

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

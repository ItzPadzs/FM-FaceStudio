from __future__ import annotations

from pathlib import Path

import pytest

from facestudio.match_engine_research.auto_skin_finder import AutoSkinFinder


def test_scan_finds_numeric_skin_and_associated_assets(tmp_path: Path) -> None:
    (tmp_path / "123.skin").write_bytes(b"skin")
    (tmp_path / "123.png").write_bytes(b"png")
    (tmp_path / "123.cfg2").write_text("eye_l=0,0,0", encoding="utf-8")
    (tmp_path / "123_hair.skin").write_bytes(b"hair")
    result = AutoSkinFinder().scan(tmp_path)
    assert result.skin_count == 2
    assert result.candidates[0].player_id == "123"
    assert result.candidates[0].score == 100
    assert result.candidates[0].face_png is not None


def test_hair_skin_is_not_a_separate_head_candidate(tmp_path: Path) -> None:
    (tmp_path / "456_hair.skin").write_bytes(b"hair")
    result = AutoSkinFinder().scan(tmp_path)
    assert result.skin_count == 1
    assert result.candidates == ()


def test_complete_candidate_ranks_above_skin_only(tmp_path: Path) -> None:
    (tmp_path / "100.skin").write_bytes(b"skin")
    (tmp_path / "200.skin").write_bytes(b"skin")
    (tmp_path / "200.png").write_bytes(b"png")
    result = AutoSkinFinder().scan(tmp_path)
    assert [item.player_id for item in result.candidates] == ["200", "100"]


def test_missing_root_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FM26_HEADS_DIR", raising=False)
    finder = AutoSkinFinder()
    monkeypatch.setattr(finder, "discover_roots", lambda explicit_root=None: ())
    with pytest.raises(ValueError, match="No FM26 heads folder"):
        finder.scan(tmp_path / "missing")

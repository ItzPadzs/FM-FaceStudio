from __future__ import annotations

from facestudio.ui.facestudio2_window import FaceStudio2Window


def test_overhaul_exposes_nine_visible_pipeline_stages() -> None:
    assert len(FaceStudio2Window.STAGES) == 9
    assert FaceStudio2Window.STAGES[0][0] == "1. Detect"
    assert FaceStudio2Window.STAGES[-1] == ("9. Finalize", 100)


def test_preview_slot_mapping_covers_real_generation_frames() -> None:
    assert FaceStudio2Window._thumbnail_slot(2) == 0
    assert FaceStudio2Window._thumbnail_slot(20) == 1
    assert FaceStudio2Window._thumbnail_slot(60) == 3
    assert FaceStudio2Window._thumbnail_slot(95) == 5
    assert FaceStudio2Window._thumbnail_slot(100) == 6

from __future__ import annotations

import json

from facestudio.ai.trained_portrait_uv import TrainedPortraitUVEngine


def test_engine_unavailable_without_manifest(tmp_path):
    engine = TrainedPortraitUVEngine(tmp_path)
    assert engine.available is False
    assert "No trained" in engine.status_message


def test_engine_requires_manifest_and_checkpoint(tmp_path):
    (tmp_path / "model-manifest.json").write_text(
        json.dumps({"format": "facestudio-portrait-uv-v1", "checkpoint": "model.pt", "image_size": 512}),
        encoding="utf-8",
    )
    engine = TrainedPortraitUVEngine(tmp_path)
    assert engine.available is False
    (tmp_path / "model.pt").write_bytes(b"checkpoint-placeholder")
    assert engine.available is True
    assert "ready" in engine.status_message.lower()

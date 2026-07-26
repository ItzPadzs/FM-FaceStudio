from pathlib import Path

from facestudio.assets.classifier import classify_asset


def test_texture_classification() -> None:
    assert classify_asset(Path("graphics/player.png")) == "Texture / Image"


def test_hair_path_classification() -> None:
    assert classify_asset(Path("models/hair/style.skin")) == "Hair"


def test_unknown_extension_classification() -> None:
    assert classify_asset(Path("data/example.unknown")) == "Other"

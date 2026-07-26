from pathlib import Path
from facestudio.utils.config import AppConfig


def test_config_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    original = AppConfig(theme="light", fm_install_path="C:/FM26", autosave_enabled=False)
    original.save(path)
    assert AppConfig.load(path) == original


def test_invalid_config_uses_defaults(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text("{invalid", encoding="utf-8")
    assert AppConfig.load(path) == AppConfig()

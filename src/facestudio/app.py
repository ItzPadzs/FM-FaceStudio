from __future__ import annotations

import sys
from PySide6.QtWidgets import QApplication

from facestudio.ui.preset_window import PresetMainWindow
from facestudio.utils.config import AppConfig
from facestudio.utils.logging_setup import configure_logging
from facestudio.utils.paths import app_data_dir
from facestudio.version import APP_NAME, APP_VERSION, PACKAGE_VERSION


def main() -> int:
    data_dir = app_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    configure_logging(data_dir / "logs")

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(f"{APP_NAME} — {APP_VERSION}")
    app.setApplicationVersion(PACKAGE_VERSION)
    app.setOrganizationName("ItzPadzs")

    config_path = data_dir / "facestudio-settings.json"
    config = AppConfig.load(config_path)
    window = PresetMainWindow(config, config_path)
    window.show()
    return app.exec()

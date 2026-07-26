from __future__ import annotations

import sys
from PySide6.QtWidgets import QApplication

from facestudio.ui.alpha_window import AlphaMainWindow
from facestudio.utils.config import AppConfig
from facestudio.utils.logging_setup import configure_logging
from facestudio.utils.paths import app_data_dir


def main() -> int:
    data_dir = app_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    configure_logging(data_dir / "logs")

    app = QApplication(sys.argv)
    app.setApplicationName("FM FaceStudio")
    app.setApplicationDisplayName("FM FaceStudio — Alpha 0.8.0 Build 2")
    app.setApplicationVersion("0.8.0-build.2")
    app.setOrganizationName("ItzPadzs")

    config_path = data_dir / "facestudio-settings.json"
    config = AppConfig.load(config_path)
    window = AlphaMainWindow(config, config_path)
    window.show()
    return app.exec()

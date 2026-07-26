from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from facestudio.utils.config import AppConfig


class SettingsPage(QWidget):
    theme_changed = Signal(str)
    settings_changed = Signal()

    def __init__(self, config: AppConfig) -> None:
        super().__init__()
        self.config = config

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 28, 30, 28)

        title = QLabel("Settings")
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        form = QFormLayout()

        self.theme = QComboBox()
        self.theme.addItems(["dark", "light"])
        self.theme.setCurrentText(config.theme)
        self.theme.currentTextChanged.connect(self._theme_changed)
        form.addRow("Theme", self.theme)

        path_row = QWidget()
        path_layout = QHBoxLayout(path_row)
        path_layout.setContentsMargins(0, 0, 0, 0)
        self.fm_path = QLineEdit(config.fm_install_path)
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._browse)
        path_layout.addWidget(self.fm_path)
        path_layout.addWidget(browse)
        form.addRow("FM26 installation", path_row)

        self.autosave = QCheckBox("Enable autosave")
        self.autosave.setChecked(config.autosave_enabled)
        form.addRow("Autosave", self.autosave)

        self.interval = QSpinBox()
        self.interval.setRange(15, 600)
        self.interval.setSuffix(" seconds")
        self.interval.setValue(config.autosave_interval_seconds)
        form.addRow("Autosave interval", self.interval)

        save = QPushButton("Save settings")
        save.setObjectName("Primary")
        save.clicked.connect(self._save)
        form.addRow("", save)

        layout.addLayout(form)
        layout.addStretch()

    def _browse(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self,
            "Choose Football Manager 26 installation",
        )
        if path:
            self.fm_path.setText(path)

    def _theme_changed(self, value: str) -> None:
        self.config.theme = value
        self.theme_changed.emit(value)
        self.settings_changed.emit()

    def _save(self) -> None:
        self.config.fm_install_path = self.fm_path.text().strip()
        self.config.autosave_enabled = self.autosave.isChecked()
        self.config.autosave_interval_seconds = self.interval.value()
        self.settings_changed.emit()

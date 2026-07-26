from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget
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
        self.theme.currentTextChanged.connect(self._change_theme)
        form.addRow("Theme", self.theme)

        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        self.fm_path = QLineEdit(config.fm_install_path)
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._browse)
        row_layout.addWidget(self.fm_path)
        row_layout.addWidget(browse)
        form.addRow("FM26 installation", row)

        save = QPushButton("Save settings")
        save.setObjectName("Primary")
        save.clicked.connect(self._save)
        form.addRow("", save)

        layout.addLayout(form)
        layout.addStretch()

    def _browse(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Choose Football Manager 26 installation")
        if path:
            self.fm_path.setText(path)

    def _change_theme(self, value: str) -> None:
        self.config.theme = value
        self.theme_changed.emit(value)
        self.settings_changed.emit()

    def _save(self) -> None:
        self.config.fm_install_path = self.fm_path.text().strip()
        self.settings_changed.emit()

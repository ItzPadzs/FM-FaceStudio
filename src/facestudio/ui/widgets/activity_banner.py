from __future__ import annotations

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QProgressBar


class ActivityBanner(QFrame):
    """Compact page-level state and busy indicator."""

    def __init__(self, message: str) -> None:
        super().__init__()
        self.setObjectName("ActivityBanner")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(12)

        self.message = QLabel(message)
        self.message.setObjectName("ActivityMessage")
        self.message.setWordWrap(True)
        layout.addWidget(self.message, 1)

        self.progress = QProgressBar()
        self.progress.setObjectName("ActivityProgress")
        self.progress.setRange(0, 0)
        self.progress.setFixedWidth(150)
        self.progress.hide()
        layout.addWidget(self.progress)

    def set_state(self, message: str, busy: bool = False) -> None:
        self.message.setText(message)
        self.progress.setVisible(busy)
        self.setProperty("busy", busy)
        self.style().unpolish(self)
        self.style().polish(self)

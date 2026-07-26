from __future__ import annotations

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QWidget


class ToastNotification(QFrame):
    """Small non-blocking notification displayed over the workspace."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("ToastNotification")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedWidth(360)
        self.hide()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 11, 10, 11)
        layout.setSpacing(10)

        self.message_label = QLabel()
        self.message_label.setObjectName("ToastMessage")
        self.message_label.setWordWrap(True)
        layout.addWidget(self.message_label, 1)

        close_button = QPushButton("×")
        close_button.setObjectName("ToastClose")
        close_button.setFixedSize(26, 26)
        close_button.clicked.connect(self.hide)
        layout.addWidget(close_button)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)

    def show_message(self, message: str, duration_ms: int = 3500) -> None:
        message = message.strip()
        if not message:
            return
        self.message_label.setText(message)
        self.adjustSize()
        self.setFixedWidth(360)
        self._position()
        self.raise_()
        self.show()
        self._timer.start(max(1500, duration_ms))

    def reposition(self) -> None:
        if self.isVisible():
            self._position()

    def _position(self) -> None:
        parent = self.parentWidget()
        if parent is None:
            return
        margin = 22
        x = max(margin, parent.width() - self.width() - margin)
        y = max(margin, parent.height() - self.sizeHint().height() - margin)
        self.move(x, y)

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class PlaceholderPage(QWidget):
    def __init__(self, title: str, description: str, status: str) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 28, 30, 28)
        heading = QLabel(title)
        heading.setObjectName("PageTitle")
        layout.addWidget(heading)
        body = QLabel(description)
        body.setObjectName("Muted")
        body.setWordWrap(True)
        layout.addWidget(body)
        status_label = QLabel(status)
        status_label.setWordWrap(True)
        status_label.setStyleSheet("margin-top: 18px; padding: 16px; border: 1px solid #343945; border-radius: 8px;")
        layout.addWidget(status_label)
        layout.addStretch()

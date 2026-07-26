from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget
from facestudio import __version__


class AboutPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 28, 30, 28)
        title = QLabel("About FM FaceStudio")
        title.setObjectName("PageTitle")
        layout.addWidget(title)
        body = QLabel(
            f"Version {__version__}\n\n"
            "Open-source Football Manager face research and generation tooling.\n\n"
            "Created by ItzPadzs with development support from ChatGPT.\n\n"
            "Current builds are read-only research software."
        )
        body.setWordWrap(True)
        body.setObjectName("Muted")
        layout.addWidget(body)
        layout.addStretch()

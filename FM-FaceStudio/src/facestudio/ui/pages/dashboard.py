from PySide6.QtWidgets import QGridLayout, QGroupBox, QLabel, QVBoxLayout, QWidget
from facestudio.fm.installation import detect_installation


class DashboardPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 28, 30, 28)
        layout.setSpacing(14)

        title = QLabel("Dashboard")
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        subtitle = QLabel("The new modular FM FaceStudio foundation is running.")
        subtitle.setObjectName("Muted")
        layout.addWidget(subtitle)

        installation = detect_installation()
        install_text = str(installation.root) if installation else "Not detected automatically"

        grid = QGridLayout()
        cards = [
            ("FM26 installation", install_text),
            ("Face AI", "Module boundary ready"),
            ("Asset index", "Module boundary ready"),
            ("Mesh system", "Module boundary ready"),
            ("Project system", "Basic model ready"),
            ("Safety", "Read-only"),
        ]
        for index, (heading, value) in enumerate(cards):
            card = QGroupBox(heading)
            card_layout = QVBoxLayout(card)
            label = QLabel(value)
            label.setWordWrap(True)
            label.setObjectName("Muted")
            card_layout.addWidget(label)
            grid.addWidget(card, index // 2, index % 2)

        layout.addLayout(grid)
        layout.addStretch()

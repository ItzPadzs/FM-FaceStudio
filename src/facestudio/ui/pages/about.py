from __future__ import annotations

from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from facestudio.version import APP_NAME, APP_TAGLINE, APP_VERSION


class AboutPage(QWidget):
    def __init__(self) -> None:
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 32, 36, 32)
        layout.setSpacing(18)

        eyebrow = QLabel(APP_NAME.upper())
        eyebrow.setObjectName("Eyebrow")
        layout.addWidget(eyebrow)

        title = QLabel(f"About {APP_NAME}")
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        subtitle = QLabel(APP_TAGLINE)
        subtitle.setObjectName("PageSubtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        hero = QFrame()
        hero.setObjectName("HeroCard")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(22, 20, 22, 20)
        hero_layout.setSpacing(8)

        product = QLabel(APP_NAME)
        product.setObjectName("SectionTitle")
        hero_layout.addWidget(product)

        version = QLabel(APP_VERSION)
        version.setObjectName("CardValue")
        hero_layout.addWidget(version)

        description = QLabel(
            "A desktop workspace for player projects, source-photo analysis, "
            "descriptor-based face matching, mesh research and validated "
            "read-only Football Manager asset exploration."
        )
        description.setWordWrap(True)
        description.setObjectName("Muted")
        hero_layout.addWidget(description)
        layout.addWidget(hero)

        details = QGridLayout()
        details.setHorizontalSpacing(14)
        details.setVerticalSpacing(14)

        cards = [
            ("Created by", "ItzPadzs"),
            ("Licence", "MIT open-source licence"),
            ("Game access", "Read-only research workflow"),
            ("Current stage", "Alpha development build"),
        ]
        for index, (heading, value) in enumerate(cards):
            card = QFrame()
            card.setObjectName("InfoCard")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(16, 14, 16, 14)
            card_layout.setSpacing(5)

            heading_label = QLabel(heading.upper())
            heading_label.setObjectName("Eyebrow")
            card_layout.addWidget(heading_label)

            value_label = QLabel(value)
            value_label.setObjectName("CardValue")
            value_label.setWordWrap(True)
            card_layout.addWidget(value_label)
            details.addWidget(card, index // 2, index % 2)

        layout.addLayout(details)

        note = QLabel(
            "FaceStudio does not claim proprietary Football Manager format "
            "support unless that capability has been independently validated."
        )
        note.setWordWrap(True)
        note.setObjectName("Muted")
        layout.addWidget(note)
        layout.addStretch()

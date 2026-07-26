from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget


class PageHeader(QWidget):
    """Consistent title and supporting copy for workspace pages."""

    def __init__(
        self,
        eyebrow: str,
        title: str,
        subtitle: str,
        actions: list[QWidget] | None = None,
    ) -> None:
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        eyebrow_label = QLabel(eyebrow.upper())
        eyebrow_label.setObjectName("Eyebrow")
        layout.addWidget(eyebrow_label)

        title_row = QHBoxLayout()
        title_row.setSpacing(10)

        title_label = QLabel(title)
        title_label.setObjectName("PageTitle")
        title_row.addWidget(title_label)
        title_row.addStretch()

        for action in actions or []:
            title_row.addWidget(action)

        layout.addLayout(title_row)

        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("PageSubtitle")
        subtitle_label.setWordWrap(True)
        layout.addWidget(subtitle_label)

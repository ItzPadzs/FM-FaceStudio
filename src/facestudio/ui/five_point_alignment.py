from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QColor, QImage, QMouseEvent, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from facestudio.ai.skin_transfer.alignment import FaceLandmarks, ManualLandmarkDetector, align_portrait, read_image


LANDMARK_NAMES = ("Left eye", "Right eye", "Nose tip", "Mouth centre", "Chin")
LANDMARK_KEYS = ("left_eye", "right_eye", "nose_tip", "mouth_centre", "chin")


class ClickableImage(QLabel):
    image_clicked = Signal(QPointF)

    def __init__(self) -> None:
        super().__init__()
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(520, 520)
        self.setObjectName("Preview")
        self._image = QImage()
        self._display_rect = self.rect()
        self.points: list[QPointF] = []

    def set_image(self, image: QImage) -> None:
        self._image = image
        self._refresh()

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt API
        super().resizeEvent(event)
        self._refresh()

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt API
        if event.button() != Qt.MouseButton.LeftButton or self._image.isNull():
            return
        position = event.position()
        if not self._display_rect.contains(position.toPoint()):
            return
        x = (position.x() - self._display_rect.x()) * self._image.width() / max(1, self._display_rect.width())
        y = (position.y() - self._display_rect.y()) * self._image.height() / max(1, self._display_rect.height())
        self.image_clicked.emit(QPointF(x, y))

    def _refresh(self) -> None:
        if self._image.isNull() or self.width() < 2 or self.height() < 2:
            return
        pixmap = QPixmap.fromImage(self._image).scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        canvas = QPixmap(self.size())
        canvas.fill(QColor("#0b1118"))
        x = (self.width() - pixmap.width()) // 2
        y = (self.height() - pixmap.height()) // 2
        self._display_rect = pixmap.rect().translated(x, y)
        painter = QPainter(canvas)
        painter.drawPixmap(x, y, pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        for index, point in enumerate(self.points):
            px = x + point.x() * pixmap.width() / max(1, self._image.width())
            py = y + point.y() * pixmap.height() / max(1, self._image.height())
            painter.setPen(QPen(QColor("#ffffff"), 2))
            painter.setBrush(QColor("#2588f4"))
            painter.drawEllipse(QPointF(px, py), 7, 7)
            painter.drawText(QPointF(px + 10, py - 8), str(index + 1))
        painter.end()
        self.setPixmap(canvas)


@dataclass(frozen=True)
class AlignmentSelection:
    landmarks: FaceLandmarks
    aligned_image: QImage

    def normalised(self, width: int, height: int) -> dict[str, list[float]]:
        result: dict[str, list[float]] = {}
        for key in LANDMARK_KEYS:
            point = getattr(self.landmarks, key)
            result[key] = [point.x() / max(1, width), point.y() / max(1, height)]
        return result


class FivePointAlignmentDialog(QDialog):
    """Collect five source-photo landmarks and preview canonical alignment."""

    def __init__(self, portrait: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.portrait_path = Path(portrait)
        self.source = read_image(self.portrait_path)
        self.selection: AlignmentSelection | None = None
        self.points: list[QPointF] = []
        self.setWindowTitle("Five-point portrait alignment")
        self.resize(1220, 760)
        self._build_ui()
        self._update_state()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        title = QLabel("Mark five facial landmarks")
        title.setStyleSheet("font-size: 24px; font-weight: 700;")
        root.addWidget(title)
        self.instructions = QLabel()
        self.instructions.setWordWrap(True)
        root.addWidget(self.instructions)

        previews = QHBoxLayout()
        source_card = QFrame()
        source_card.setObjectName("Card")
        source_layout = QVBoxLayout(source_card)
        source_layout.addWidget(QLabel("Source portrait — click in order"))
        self.source_view = ClickableImage()
        self.source_view.set_image(self.source)
        self.source_view.image_clicked.connect(self._add_point)
        source_layout.addWidget(self.source_view, 1)
        previews.addWidget(source_card, 1)

        aligned_card = QFrame()
        aligned_card.setObjectName("Card")
        aligned_layout = QVBoxLayout(aligned_card)
        aligned_layout.addWidget(QLabel("Canonical aligned preview"))
        self.aligned_view = QLabel("Place all five points to preview alignment")
        self.aligned_view.setObjectName("Preview")
        self.aligned_view.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.aligned_view.setMinimumSize(520, 520)
        aligned_layout.addWidget(self.aligned_view, 1)
        previews.addWidget(aligned_card, 1)
        root.addLayout(previews, 1)

        actions = QHBoxLayout()
        undo = QPushButton("Undo Point")
        undo.clicked.connect(self._undo)
        actions.addWidget(undo)
        reset = QPushButton("Reset")
        reset.clicked.connect(self._reset)
        actions.addWidget(reset)
        actions.addStretch()
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        actions.addWidget(cancel)
        self.confirm_button = QPushButton("Use Alignment")
        self.confirm_button.setObjectName("Primary")
        self.confirm_button.clicked.connect(self._confirm)
        actions.addWidget(self.confirm_button)
        root.addLayout(actions)

    def _add_point(self, point: QPointF) -> None:
        if len(self.points) >= len(LANDMARK_NAMES):
            return
        self.points.append(point)
        self.source_view.points = list(self.points)
        self.source_view._refresh()
        self._update_state()

    def _undo(self) -> None:
        if self.points:
            self.points.pop()
            self.source_view.points = list(self.points)
            self.source_view._refresh()
            self._update_state()

    def _reset(self) -> None:
        self.points.clear()
        self.selection = None
        self.source_view.points = []
        self.source_view._refresh()
        self.aligned_view.clear()
        self.aligned_view.setText("Place all five points to preview alignment")
        self._update_state()

    def _landmarks(self) -> FaceLandmarks:
        if len(self.points) != 5:
            raise ValueError("Five landmarks are required")
        return FaceLandmarks(*self.points)

    def _update_state(self) -> None:
        index = len(self.points)
        if index < len(LANDMARK_NAMES):
            self.instructions.setText(
                f"Point {index + 1} of 5: click the {LANDMARK_NAMES[index].lower()}. "
                "Order: left eye, right eye, nose tip, mouth centre, chin."
            )
            self.confirm_button.setEnabled(False)
            return
        try:
            landmarks = self._landmarks()
            result = align_portrait(self.source, ManualLandmarkDetector(landmarks))
            self.selection = AlignmentSelection(landmarks, result.image)
            pixmap = QPixmap.fromImage(result.image).scaled(
                self.aligned_view.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.aligned_view.setPixmap(pixmap)
            self.instructions.setText("Alignment preview ready. Confirm it or undo a point and try again.")
            self.confirm_button.setEnabled(True)
        except Exception as exc:
            self.selection = None
            self.confirm_button.setEnabled(False)
            self.instructions.setText(f"Alignment could not be previewed: {exc}")

    def _confirm(self) -> None:
        if self.selection is None:
            QMessageBox.warning(self, "Alignment incomplete", "Place all five landmarks first.")
            return
        self.accept()

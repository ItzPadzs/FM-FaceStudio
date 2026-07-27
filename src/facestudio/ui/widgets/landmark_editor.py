from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QImage, QMouseEvent, QPainter, QPen
from PySide6.QtWidgets import QWidget

from facestudio.match_engine_research.one_click_face_builder import LANDMARK_ORDER, Landmark


class LandmarkEditor(QWidget):
    """Interactive portrait landmark canvas.

    The portrait is fitted into the widget without distortion. Users select the
    nearest visible landmark and drag it directly over the corresponding facial
    feature. Coordinates emitted by ``landmark_moved`` are normalised to the
    original image, so measurements remain independent of window size.
    """

    landmark_moved = Signal(str, float, float)
    landmark_selected = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(440, 440)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self._image = QImage()
        self._landmarks: tuple[Landmark, ...] = ()
        self._selected: str | None = None
        self._dragging = False
        self._hovered: str | None = None

    def set_content(self, image: QImage, landmarks: tuple[Landmark, ...]) -> None:
        self._image = image
        self._landmarks = landmarks
        if self._selected not in {point.name for point in landmarks}:
            self._selected = landmarks[0].name if landmarks else None
        self.update()

    def clear(self, message: str = "Choose one clear front-facing photograph") -> None:
        self._image = QImage()
        self._landmarks = ()
        self._selected = None
        self._empty_message = message
        self.update()

    def select_landmark(self, name: str) -> None:
        if name in {point.name for point in self._landmarks}:
            self._selected = name
            self.landmark_selected.emit(name)
            self.update()

    def image_rect(self) -> QRectF:
        if self._image.isNull() or self.width() <= 0 or self.height() <= 0:
            return QRectF()
        scale = min(self.width() / self._image.width(), self.height() / self._image.height())
        width = self._image.width() * scale
        height = self._image.height() * scale
        return QRectF((self.width() - width) / 2, (self.height() - height) / 2, width, height)

    @staticmethod
    def normalise_point(point: QPointF, image_rect: QRectF) -> tuple[float, float]:
        if image_rect.width() <= 0 or image_rect.height() <= 0:
            return 0.0, 0.0
        x = (point.x() - image_rect.left()) / image_rect.width()
        y = (point.y() - image_rect.top()) / image_rect.height()
        return max(0.0, min(1.0, x)), max(0.0, min(1.0, y))

    def _widget_point(self, landmark: Landmark) -> QPointF:
        rect = self.image_rect()
        return QPointF(rect.left() + landmark.x * rect.width(), rect.top() + landmark.y * rect.height())

    def _nearest_landmark(self, position: QPointF, radius: float = 18.0) -> str | None:
        best_name: str | None = None
        best_distance = radius
        for point in self._landmarks:
            widget_point = self._widget_point(point)
            distance = ((widget_point.x() - position.x()) ** 2 + (widget_point.y() - position.y()) ** 2) ** 0.5
            if distance <= best_distance:
                best_distance = distance
                best_name = point.name
        return best_name

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton or self._image.isNull():
            return super().mousePressEvent(event)
        selected = self._nearest_landmark(event.position())
        if selected is None:
            return
        self._selected = selected
        self._dragging = True
        self.landmark_selected.emit(selected)
        self.setCursor(Qt.CursorShape.ClosedHandCursor)
        self._emit_move(event.position())
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._dragging and self._selected:
            self._emit_move(event.position())
            return
        hovered = self._nearest_landmark(event.position())
        if hovered != self._hovered:
            self._hovered = hovered
            self.setCursor(Qt.CursorShape.OpenHandCursor if hovered else Qt.CursorShape.CrossCursor)
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._dragging:
            self._emit_move(event.position())
            self._dragging = False
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            self.update()
            return
        super().mouseReleaseEvent(event)

    def _emit_move(self, position: QPointF) -> None:
        if not self._selected:
            return
        x, y = self.normalise_point(position, self.image_rect())
        self.landmark_moved.emit(self._selected, x, y)

    def paintEvent(self, event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(self.rect(), QColor(12, 15, 20))
        if self._image.isNull():
            painter.setPen(QColor(180, 186, 196))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, getattr(self, "_empty_message", "Choose one clear front-facing photograph"))
            return

        rect = self.image_rect()
        painter.drawImage(rect, self._image)
        points = {point.name: self._widget_point(point) for point in self._landmarks}
        chains = (
            ("face_top", "left_temple", "left_jaw", "chin", "right_jaw", "right_temple", "face_top"),
            ("left_eye", "right_eye"),
            ("nose_bridge", "nose_tip", "chin"),
            ("left_mouth", "right_mouth"),
        )
        painter.setPen(QPen(QColor(50, 178, 255, 225), 2.5))
        for chain in chains:
            for first, second in zip(chain, chain[1:]):
                if first in points and second in points:
                    painter.drawLine(points[first], points[second])

        for name in LANDMARK_ORDER:
            if name not in points:
                continue
            centre = points[name]
            selected = name == self._selected
            hovered = name == self._hovered
            radius = 10.0 if selected else 8.0 if hovered else 6.0
            painter.setPen(QPen(QColor(255, 255, 255), 2.0 if selected else 1.0))
            painter.setBrush(QColor(255, 190, 65) if selected else QColor(65, 255, 150))
            painter.drawEllipse(centre, radius, radius)
            if selected:
                label_rect = QRectF(centre.x() + 12, centre.y() - 18, 150, 28)
                painter.setPen(QColor(255, 255, 255))
                painter.drawText(label_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, name.replace("_", " "))

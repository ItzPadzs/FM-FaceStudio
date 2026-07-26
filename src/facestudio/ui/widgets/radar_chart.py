from __future__ import annotations

import math

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from facestudio.matching.models import FaceDescriptor


class RadarChart(QWidget):
    LABELS = ("Face ratio", "Eye spacing", "Eye line", "Mouth line")
    RANGES = (
        (0.8, 1.7),
        (0.20, 0.50),
        (0.20, 0.60),
        (0.55, 0.90),
    )

    def __init__(self) -> None:
        super().__init__()
        self.primary: FaceDescriptor | None = None
        self.secondary: FaceDescriptor | None = None
        self.setMinimumHeight(300)

    def set_descriptors(
        self,
        primary: FaceDescriptor | None,
        secondary: FaceDescriptor | None = None,
    ) -> None:
        self.primary = primary
        self.secondary = secondary
        self.update()

    def _values(self, descriptor: FaceDescriptor) -> list[float]:
        raw = [
            descriptor.face_height_width_ratio,
            descriptor.inter_eye_face_width_ratio,
            descriptor.eye_line_face_height_ratio,
            descriptor.mouth_line_face_height_ratio,
        ]
        values = []
        for value, (minimum, maximum) in zip(raw, self.RANGES):
            values.append(max(0.0, min(1.0, (value - minimum) / (maximum - minimum))))
        return values

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), self.palette().window())

        centre = QPointF(self.width() / 2.0, self.height() / 2.0)
        radius = min(self.width(), self.height()) * 0.34
        count = len(self.LABELS)

        grid_pen = QPen(self.palette().mid().color())
        painter.setPen(grid_pen)
        for ring in range(1, 5):
            ring_radius = radius * ring / 4
            path = QPainterPath()
            for index in range(count):
                angle = -math.pi / 2 + index * 2 * math.pi / count
                point = QPointF(
                    centre.x() + math.cos(angle) * ring_radius,
                    centre.y() + math.sin(angle) * ring_radius,
                )
                if index == 0:
                    path.moveTo(point)
                else:
                    path.lineTo(point)
            path.closeSubpath()
            painter.drawPath(path)

        for index, label in enumerate(self.LABELS):
            angle = -math.pi / 2 + index * 2 * math.pi / count
            endpoint = QPointF(
                centre.x() + math.cos(angle) * radius,
                centre.y() + math.sin(angle) * radius,
            )
            painter.drawLine(centre, endpoint)
            label_point = QPointF(
                centre.x() + math.cos(angle) * (radius + 28),
                centre.y() + math.sin(angle) * (radius + 28),
            )
            painter.drawText(
                int(label_point.x() - 55),
                int(label_point.y() - 10),
                110,
                20,
                Qt.AlignmentFlag.AlignCenter,
                label,
            )

        def draw_descriptor(descriptor: FaceDescriptor, width: float, dashed: bool) -> None:
            values = self._values(descriptor)
            pen = QPen(self.palette().highlight().color())
            pen.setWidthF(width)
            if dashed:
                pen.setStyle(Qt.PenStyle.DashLine)
            painter.setPen(pen)
            path = QPainterPath()
            for index, value in enumerate(values):
                angle = -math.pi / 2 + index * 2 * math.pi / count
                point = QPointF(
                    centre.x() + math.cos(angle) * radius * value,
                    centre.y() + math.sin(angle) * radius * value,
                )
                if index == 0:
                    path.moveTo(point)
                else:
                    path.lineTo(point)
            path.closeSubpath()
            painter.drawPath(path)

        if self.primary is not None:
            draw_descriptor(self.primary, 2.4, False)
        if self.secondary is not None:
            draw_descriptor(self.secondary, 1.7, True)

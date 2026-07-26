from __future__ import annotations

import math

from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QMouseEvent, QPainter, QPen, QWheelEvent
from PySide6.QtWidgets import QWidget

from facestudio.mesh.model import MeshData, Vec3


class MeshViewport(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.mesh: MeshData | None = None
        self.yaw = -25.0
        self.pitch = 15.0
        self.zoom = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.show_grid = True
        self.show_vertices = True
        self.last_mouse_position: QPoint | None = None
        self.setMinimumSize(420, 360)
        self.setMouseTracking(True)

    def set_mesh(self, mesh: MeshData | None) -> None:
        self.mesh = mesh
        self.reset_view()

    def reset_view(self) -> None:
        self.set_view(-25.0, 15.0)

    def set_view(self, yaw: float, pitch: float) -> None:
        self.yaw = yaw
        self.pitch = pitch
        self.zoom = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.update()

    def zoom_in(self) -> None:
        self.zoom = min(8.0, self.zoom * 1.2)
        self.update()

    def zoom_out(self) -> None:
        self.zoom = max(0.15, self.zoom / 1.2)
        self.update()

    def set_grid_visible(self, visible: bool) -> None:
        self.show_grid = visible
        self.update()

    def set_vertices_visible(self, visible: bool) -> None:
        self.show_vertices = visible
        self.update()

    def _rotate(self, vertex: Vec3) -> tuple[float, float, float]:
        yaw = math.radians(self.yaw)
        pitch = math.radians(self.pitch)
        x1 = vertex.x * math.cos(yaw) + vertex.z * math.sin(yaw)
        z1 = -vertex.x * math.sin(yaw) + vertex.z * math.cos(yaw)
        y2 = vertex.y * math.cos(pitch) - z1 * math.sin(pitch)
        z2 = vertex.y * math.sin(pitch) + z1 * math.cos(pitch)
        return x1, y2, z2

    def _normalised_vertices(self) -> list[Vec3]:
        if self.mesh is None:
            return []
        minimum, maximum = self.mesh.bounds()
        centre_x = (minimum.x + maximum.x) / 2.0
        centre_y = (minimum.y + maximum.y) / 2.0
        centre_z = (minimum.z + maximum.z) / 2.0
        largest = max(
            maximum.x - minimum.x,
            maximum.y - minimum.y,
            maximum.z - minimum.z,
            0.000001,
        )
        return [
            Vec3(
                (vertex.x - centre_x) / largest,
                (vertex.y - centre_y) / largest,
                (vertex.z - centre_z) / largest,
            )
            for vertex in self.mesh.vertices
        ]

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), self.palette().window())

        centre = QPointF(
            self.width() / 2.0 + self.pan_x,
            self.height() / 2.0 + self.pan_y,
        )
        if self.show_grid:
            grid_pen = QPen(self.palette().mid().color())
            grid_pen.setWidth(1)
            painter.setPen(grid_pen)
            spacing = 40
            for x in range(int(centre.x()) % spacing, self.width(), spacing):
                painter.drawLine(x, 0, x, self.height())
            for y in range(int(centre.y()) % spacing, self.height(), spacing):
                painter.drawLine(0, y, self.width(), y)

        if self.mesh is None:
            painter.setPen(self.palette().text().color())
            painter.drawText(
                self.rect(),
                Qt.AlignmentFlag.AlignCenter,
                "Open a Wavefront OBJ file to preview it.\n"
                "Drag to rotate · Mouse wheel to zoom · Shift-drag to pan",
            )
            return

        vertices = self._normalised_vertices()
        scale = min(self.width(), self.height()) * 0.72 * self.zoom
        projected: list[tuple[QPointF, float]] = []
        for vertex in vertices:
            x, y, z = self._rotate(vertex)
            perspective = 1.0 / max(0.35, 2.4 - z * 0.7)
            projected.append(
                (
                    QPointF(
                        centre.x() + x * scale * perspective,
                        centre.y() - y * scale * perspective,
                    ),
                    z,
                )
            )

        mesh_pen = QPen(self.palette().highlight().color())
        mesh_pen.setWidthF(1.2)
        painter.setPen(mesh_pen)
        edges = sorted(
            self.mesh.edges,
            key=lambda edge: (
                projected[edge[0]][1] + projected[edge[1]][1]
            ) / 2.0,
        )
        for start, end in edges:
            painter.drawLine(projected[start][0], projected[end][0])

        if self.show_vertices and self.mesh.vertex_count <= 2500:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(self.palette().highlight())
            for point, _ in projected:
                painter.drawEllipse(point, 1.8, 1.8)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.last_mouse_position = event.position().toPoint()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self.last_mouse_position is None:
            return
        current = event.position().toPoint()
        delta = current - self.last_mouse_position
        self.last_mouse_position = current
        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            self.pan_x += delta.x()
            self.pan_y += delta.y()
        else:
            self.yaw += delta.x() * 0.45
            self.pitch = max(-89.0, min(89.0, self.pitch + delta.y() * 0.45))
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self.last_mouse_position = None

    def wheelEvent(self, event: QWheelEvent) -> None:
        factor = 1.12 if event.angleDelta().y() > 0 else 1 / 1.12
        self.zoom = max(0.15, min(8.0, self.zoom * factor))
        self.update()

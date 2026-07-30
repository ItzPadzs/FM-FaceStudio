from __future__ import annotations

from array import array
from dataclasses import dataclass
from math import cos, pi, sin
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QMatrix4x4, QVector3D
from PySide6.QtOpenGL import QOpenGLBuffer, QOpenGLShader, QOpenGLShaderProgram, QOpenGLTexture, QOpenGLVertexArrayObject
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtWidgets import QCheckBox, QDialog, QHBoxLayout, QLabel, QPushButton, QSlider, QVBoxLayout


@dataclass(frozen=True)
class HeadMesh:
    vertices: tuple[float, ...]
    triangle_indices: tuple[int, ...]
    line_indices: tuple[int, ...]


def build_head_mesh(longitude_segments: int = 64, latitude_segments: int = 48) -> HeadMesh:
    """Build a lightweight UV-mapped head proxy.

    The mesh is intentionally generic: it is a review surface, not a game-owned
    head model. UV coordinates remain regular and the generated texture itself
    is never modified.
    """
    if longitude_segments < 8 or latitude_segments < 6:
        raise ValueError("Head mesh requires at least 8 longitude and 6 latitude segments")

    vertices: list[float] = []
    triangles: list[int] = []
    edges: set[tuple[int, int]] = set()

    for latitude in range(latitude_segments + 1):
        v = latitude / latitude_segments
        phi = pi * v
        y = cos(phi)
        ring = sin(phi)
        for longitude in range(longitude_segments + 1):
            u = longitude / longitude_segments
            theta = 2.0 * pi * u

            # A slightly narrower skull, fuller jaw and subtle facial projection.
            jaw_factor = 0.82 + 0.18 * max(0.0, y)
            x = 0.78 * ring * cos(theta) * jaw_factor
            z = 0.92 * ring * sin(theta)
            front = max(0.0, sin(theta))
            nose = 0.16 * front * max(0.0, 1.0 - abs(y + 0.02) * 2.8)
            chin = 0.07 * front * max(0.0, (-y - 0.35) * 2.0)
            z += nose + chin
            y *= 1.08

            # Position, approximate normal, UV.
            nx, ny, nz = x / 0.78, y / 1.08, z / 0.98
            length = max((nx * nx + ny * ny + nz * nz) ** 0.5, 1e-6)
            vertices.extend((x, y, z, nx / length, ny / length, nz / length, u, 1.0 - v))

    stride = longitude_segments + 1
    for latitude in range(latitude_segments):
        for longitude in range(longitude_segments):
            a = latitude * stride + longitude
            b = a + 1
            c = a + stride
            d = c + 1
            triangles.extend((a, c, b, b, c, d))
            for first, second in ((a, b), (a, c), (b, d), (c, d)):
                edges.add((min(first, second), max(first, second)))

    lines = [index for edge in sorted(edges) for index in edge]
    return HeadMesh(tuple(vertices), tuple(triangles), tuple(lines))


class HeadPreviewWidget(QOpenGLWidget):
    """Interactive textured head proxy rendered with Qt OpenGL."""

    def __init__(self, texture_path: Path | None = None, parent=None) -> None:
        super().__init__(parent)
        self.texture_path = Path(texture_path) if texture_path else None
        self.rotation_x = -5.0
        self.rotation_y = 0.0
        self.zoom = 2.75
        self.light_strength = 0.85
        self.wireframe = False
        self.last_mouse_position = None
        self.mesh = build_head_mesh()
        self.program: QOpenGLShaderProgram | None = None
        self.texture: QOpenGLTexture | None = None
        self.vertex_buffer = QOpenGLBuffer(QOpenGLBuffer.Type.VertexBuffer)
        self.triangle_buffer = QOpenGLBuffer(QOpenGLBuffer.Type.IndexBuffer)
        self.line_buffer = QOpenGLBuffer(QOpenGLBuffer.Type.IndexBuffer)
        self.vao = QOpenGLVertexArrayObject()
        self.setMinimumSize(640, 520)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def set_texture(self, texture_path: Path) -> None:
        self.texture_path = Path(texture_path)
        if self.context() and self.context().isValid():
            self.makeCurrent()
            self._load_texture()
            self.doneCurrent()
            self.update()

    def set_wireframe(self, enabled: bool) -> None:
        self.wireframe = enabled
        self.update()

    def set_light_strength(self, value: int) -> None:
        self.light_strength = max(0.15, min(1.5, value / 100.0))
        self.update()

    def reset_view(self) -> None:
        self.rotation_x = -5.0
        self.rotation_y = 0.0
        self.zoom = 2.75
        self.update()

    def initializeGL(self) -> None:
        functions = self.context().functions()
        functions.glEnable(0x0B71)  # GL_DEPTH_TEST
        functions.glEnable(0x0B44)  # GL_CULL_FACE
        functions.glClearColor(0.055, 0.065, 0.085, 1.0)

        self.program = QOpenGLShaderProgram(self)
        vertex_shader = """
            attribute highp vec3 position;
            attribute highp vec3 normal;
            attribute highp vec2 texcoord;
            uniform highp mat4 mvp;
            uniform highp mat4 model;
            varying highp vec3 worldNormal;
            varying highp vec2 uv;
            void main() {
                gl_Position = mvp * vec4(position, 1.0);
                worldNormal = normalize((model * vec4(normal, 0.0)).xyz);
                uv = texcoord;
            }
        """
        fragment_shader = """
            uniform sampler2D faceTexture;
            uniform highp float lightStrength;
            uniform bool wireframeMode;
            varying highp vec3 worldNormal;
            varying highp vec2 uv;
            void main() {
                if (wireframeMode) {
                    gl_FragColor = vec4(0.82, 0.88, 0.96, 1.0);
                    return;
                }
                highp vec3 lightDirection = normalize(vec3(-0.35, 0.45, 0.82));
                highp float diffuse = max(dot(normalize(worldNormal), lightDirection), 0.0);
                highp float lighting = 0.34 + diffuse * lightStrength;
                highp vec4 base = texture2D(faceTexture, uv);
                gl_FragColor = vec4(base.rgb * lighting, base.a);
            }
        """
        if not self.program.addShaderFromSourceCode(QOpenGLShader.ShaderTypeBit.Vertex, vertex_shader):
            raise RuntimeError(self.program.log())
        if not self.program.addShaderFromSourceCode(QOpenGLShader.ShaderTypeBit.Fragment, fragment_shader):
            raise RuntimeError(self.program.log())
        if not self.program.link():
            raise RuntimeError(self.program.log())

        self.vao.create()
        self.vao.bind()
        self.vertex_buffer.create()
        self.vertex_buffer.bind()
        vertex_data = array("f", self.mesh.vertices)
        self.vertex_buffer.allocate(vertex_data.tobytes(), len(vertex_data) * vertex_data.itemsize)

        stride = 8 * 4
        self.program.bind()
        self.program.enableAttributeArray("position")
        self.program.setAttributeBuffer("position", 0x1406, 0, 3, stride)  # GL_FLOAT
        self.program.enableAttributeArray("normal")
        self.program.setAttributeBuffer("normal", 0x1406, 3 * 4, 3, stride)
        self.program.enableAttributeArray("texcoord")
        self.program.setAttributeBuffer("texcoord", 0x1406, 6 * 4, 2, stride)

        self.triangle_buffer.create()
        self.triangle_buffer.bind()
        triangle_data = array("I", self.mesh.triangle_indices)
        self.triangle_buffer.allocate(triangle_data.tobytes(), len(triangle_data) * triangle_data.itemsize)

        self.line_buffer.create()
        self.line_buffer.bind()
        line_data = array("I", self.mesh.line_indices)
        self.line_buffer.allocate(line_data.tobytes(), len(line_data) * line_data.itemsize)

        self.vao.release()
        self.program.release()
        self._load_texture()

    def _load_texture(self) -> None:
        if self.texture is not None:
            self.texture.destroy()
            self.texture = None
        if self.texture_path is None:
            return
        image = QImage(str(self.texture_path)).convertToFormat(QImage.Format.Format_RGBA8888)
        if image.isNull():
            return
        self.texture = QOpenGLTexture(image.mirrored())
        self.texture.setMinificationFilter(QOpenGLTexture.Filter.LinearMipMapLinear)
        self.texture.setMagnificationFilter(QOpenGLTexture.Filter.Linear)
        self.texture.setWrapMode(QOpenGLTexture.WrapMode.Repeat)

    def resizeGL(self, width: int, height: int) -> None:
        self.context().functions().glViewport(0, 0, width, max(height, 1))

    def paintGL(self) -> None:
        functions = self.context().functions()
        functions.glClear(0x00004000 | 0x00000100)  # COLOR_BUFFER_BIT | DEPTH_BUFFER_BIT
        if self.program is None or self.texture is None:
            return

        projection = QMatrix4x4()
        projection.perspective(38.0, self.width() / max(self.height(), 1), 0.1, 100.0)
        view = QMatrix4x4()
        view.lookAt(QVector3D(0.0, 0.0, self.zoom), QVector3D(0.0, 0.0, 0.0), QVector3D(0.0, 1.0, 0.0))
        model = QMatrix4x4()
        model.rotate(self.rotation_x, 1.0, 0.0, 0.0)
        model.rotate(self.rotation_y, 0.0, 1.0, 0.0)

        self.program.bind()
        self.program.setUniformValue("mvp", projection * view * model)
        self.program.setUniformValue("model", model)
        self.program.setUniformValue("lightStrength", self.light_strength)
        self.program.setUniformValue("wireframeMode", self.wireframe)
        self.program.setUniformValue("faceTexture", 0)
        self.texture.bind(0)
        self.vao.bind()

        if self.wireframe:
            self.line_buffer.bind()
            functions.glDrawElements(0x0001, len(self.mesh.line_indices), 0x1405, None)  # GL_LINES, GL_UNSIGNED_INT
        else:
            self.triangle_buffer.bind()
            functions.glDrawElements(0x0004, len(self.mesh.triangle_indices), 0x1405, None)  # GL_TRIANGLES

        self.vao.release()
        self.texture.release()
        self.program.release()

    def mousePressEvent(self, event) -> None:
        self.last_mouse_position = event.position()

    def mouseMoveEvent(self, event) -> None:
        if self.last_mouse_position is None:
            return
        delta = event.position() - self.last_mouse_position
        if event.buttons() & Qt.MouseButton.LeftButton:
            self.rotation_y += delta.x() * 0.55
            self.rotation_x += delta.y() * 0.55
            self.rotation_x = max(-85.0, min(85.0, self.rotation_x))
            self.update()
        self.last_mouse_position = event.position()

    def mouseReleaseEvent(self, event) -> None:
        self.last_mouse_position = None

    def wheelEvent(self, event) -> None:
        self.zoom -= event.angleDelta().y() / 1200.0
        self.zoom = max(1.65, min(5.5, self.zoom))
        self.update()


class HeadPreviewDialog(QDialog):
    def __init__(self, texture_path: Path, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("FaceStudio 3D Head Preview")
        self.resize(900, 720)

        layout = QVBoxLayout(self)
        description = QLabel(
            "Drag to rotate • Mouse wheel to zoom • Preview only — the exported UV texture is not changed"
        )
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(description)

        self.preview = HeadPreviewWidget(texture_path, self)
        layout.addWidget(self.preview, 1)

        controls = QHBoxLayout()
        self.wireframe = QCheckBox("Wireframe")
        self.wireframe.toggled.connect(self.preview.set_wireframe)
        controls.addWidget(self.wireframe)
        controls.addWidget(QLabel("Lighting"))
        lighting = QSlider(Qt.Orientation.Horizontal)
        lighting.setRange(15, 150)
        lighting.setValue(85)
        lighting.valueChanged.connect(self.preview.set_light_strength)
        controls.addWidget(lighting, 1)
        reset = QPushButton("Reset View")
        reset.clicked.connect(self.preview.reset_view)
        controls.addWidget(reset)
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        controls.addWidget(close)
        layout.addLayout(controls)

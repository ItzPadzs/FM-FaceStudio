from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRect


@dataclass(frozen=True)
class FixedUVGeometry:
    """Canonical 1024x1024 placement contract for working FM diffuse textures.

    Coordinates are normalised so the same profile can validate and render any square
    output size. The profile describes the stable front-face area visible across the
    supplied working textures; donor artwork still supplies scalp, ears, neck and other
    regions that a frontal portrait cannot observe.
    """

    width: int = 1024
    height: int = 1024

    # Full continuous inner-face destination.
    face_left: float = 0.205
    face_top: float = 0.120
    face_right: float = 0.795
    face_bottom: float = 0.790

    # Stable feature centres measured as fractions of the full atlas.
    left_eye: tuple[float, float] = (0.405, 0.360)
    right_eye: tuple[float, float] = (0.595, 0.360)
    nose: tuple[float, float] = (0.500, 0.505)
    mouth: tuple[float, float] = (0.500, 0.625)
    chin: tuple[float, float] = (0.500, 0.735)

    def validate(self) -> None:
        if self.width != self.height or self.width <= 0:
            raise ValueError("FM UV output must use a positive square atlas")
        values = (self.face_left, self.face_top, self.face_right, self.face_bottom)
        if not all(0.0 <= value <= 1.0 for value in values):
            raise ValueError("UV face bounds must be normalised")
        if self.face_left >= self.face_right or self.face_top >= self.face_bottom:
            raise ValueError("UV face bounds are invalid")
        for point in (self.left_eye, self.right_eye, self.nose, self.mouth, self.chin):
            if not all(0.0 <= value <= 1.0 for value in point):
                raise ValueError("UV feature anchors must be normalised")

    def face_rect(self, width: int, height: int) -> QRect:
        self.validate()
        return QRect(
            round(width * self.face_left),
            round(height * self.face_top),
            max(1, round(width * (self.face_right - self.face_left))),
            max(1, round(height * (self.face_bottom - self.face_top))),
        )

    @staticmethod
    def point(anchor: tuple[float, float], width: int, height: int) -> QPointF:
        return QPointF(anchor[0] * width, anchor[1] * height)


FM_FIXED_UV = FixedUVGeometry()

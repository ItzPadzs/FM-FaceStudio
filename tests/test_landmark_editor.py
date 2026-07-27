from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF

from facestudio.ui.widgets.landmark_editor import LandmarkEditor


def test_normalise_point_maps_fitted_image_coordinates() -> None:
    image_rect = QRectF(100.0, 50.0, 400.0, 600.0)

    assert LandmarkEditor.normalise_point(QPointF(100.0, 50.0), image_rect) == (0.0, 0.0)
    assert LandmarkEditor.normalise_point(QPointF(300.0, 350.0), image_rect) == (0.5, 0.5)
    assert LandmarkEditor.normalise_point(QPointF(500.0, 650.0), image_rect) == (1.0, 1.0)


def test_normalise_point_clamps_drag_outside_image() -> None:
    image_rect = QRectF(100.0, 50.0, 400.0, 600.0)

    assert LandmarkEditor.normalise_point(QPointF(-100.0, -100.0), image_rect) == (0.0, 0.0)
    assert LandmarkEditor.normalise_point(QPointF(900.0, 900.0), image_rect) == (1.0, 1.0)


def test_normalise_point_handles_empty_image_rect() -> None:
    assert LandmarkEditor.normalise_point(QPointF(50.0, 50.0), QRectF()) == (0.0, 0.0)

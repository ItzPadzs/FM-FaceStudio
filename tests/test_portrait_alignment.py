import json
from pathlib import Path

from PySide6.QtCore import QPointF, QSize
from PySide6.QtGui import QColor, QImage

from facestudio.ai.skin_transfer.alignment import FaceLandmarks, ManualLandmarkDetector, align_portrait, canonical_landmarks
from facestudio.ai.skin_transfer.profiles import load_mask_profile


def test_manual_alignment_places_eyes_in_canonical_positions() -> None:
    image = QImage(800, 1000, QImage.Format.Format_RGB32)
    image.fill(QColor(120, 90, 70))
    source = FaceLandmarks(
        left_eye=QPointF(250, 360),
        right_eye=QPointF(550, 380),
        nose_tip=QPointF(405, 525),
        mouth_centre=QPointF(405, 655),
        chin=QPointF(410, 830),
    )
    result = align_portrait(image, ManualLandmarkDetector(source), QSize(1024, 1024))
    assert result.image.size() == QSize(1024, 1024)
    assert result.detector == "manual-landmarks-v1"
    assert not result.transform.isIdentity()


def test_canonical_landmarks_are_stable() -> None:
    landmarks = canonical_landmarks(QSize(1000, 1000))
    assert landmarks.left_eye == QPointF(390, 370)
    assert landmarks.right_eye == QPointF(610, 370)
    assert landmarks.mouth_centre == QPointF(500, 640)


def test_mask_profile_validation(tmp_path: Path) -> None:
    path = tmp_path / "profile.json"
    path.write_text(json.dumps({
        "id": "test-v1",
        "name": "Test",
        "regions": {
            "eyes": [[0.3, 0.3, 0.1, 0.1], [0.6, 0.3, 0.1, 0.1]],
            "nostrils": [0.45, 0.5, 0.1, 0.05],
            "mouth": [0.4, 0.6, 0.2, 0.1],
            "ears": [[0.05, 0.3, 0.1, 0.3], [0.85, 0.3, 0.1, 0.3]]
        }
    }), encoding="utf-8")
    profile = load_mask_profile(path)
    assert profile.profile_id == "test-v1"
    assert profile.regions.mouth.width() == 0.2

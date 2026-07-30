from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPointF
from PySide6.QtGui import QColor, QImage

from facestudio.ai.skin_transfer.alignment import FaceLandmarks, ManualLandmarkDetector, align_portrait
from facestudio.project_workspace import FaceStudioProject
from facestudio.ui.five_point_alignment import AlignmentSelection, LANDMARK_KEYS, LANDMARK_NAMES


def test_five_point_contract_is_stable() -> None:
    assert LANDMARK_NAMES == ("Left eye", "Right eye", "Nose tip", "Mouth centre", "Chin")
    assert LANDMARK_KEYS == ("left_eye", "right_eye", "nose_tip", "mouth_centre", "chin")


def test_alignment_selection_exports_normalised_landmarks() -> None:
    landmarks = FaceLandmarks(
        left_eye=QPointF(20, 30),
        right_eye=QPointF(80, 30),
        nose_tip=QPointF(50, 50),
        mouth_centre=QPointF(50, 70),
        chin=QPointF(50, 90),
    )
    source = QImage(100, 100, QImage.Format.Format_RGB32)
    source.fill(QColor("#9c6b54"))
    aligned = align_portrait(source, ManualLandmarkDetector(landmarks)).image
    selection = AlignmentSelection(landmarks, aligned)
    values = selection.normalised(100, 100)
    assert values["left_eye"] == [0.2, 0.3]
    assert values["chin"] == [0.5, 0.9]


def test_project_round_trip_preserves_alignment(tmp_path: Path) -> None:
    source = tmp_path / "portrait.png"
    aligned = tmp_path / "project" / "alignment" / "aligned-portrait.png"
    source.write_bytes(b"source")
    aligned.parent.mkdir(parents=True)
    aligned.write_bytes(b"aligned")
    landmarks = {
        "left_eye": [0.35, 0.36],
        "right_eye": [0.65, 0.36],
        "nose_tip": [0.50, 0.52],
        "mouth_centre": [0.50, 0.65],
        "chin": [0.50, 0.82],
    }
    project = FaceStudioProject(
        name="Aligned Player",
        directory=tmp_path / "project",
        portrait=source,
        aligned_portrait=aligned,
        alignment_landmarks=landmarks,
    )
    manifest = project.save()
    loaded = FaceStudioProject.load(manifest)
    assert loaded.aligned_portrait == aligned
    assert loaded.alignment_landmarks == landmarks

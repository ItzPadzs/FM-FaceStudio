import json
from pathlib import Path

import cv2
import numpy as np
import pytest

from facestudio.ai.analyzer import FaceAnalysisError, FaceAnalyzer


def test_blank_image_has_no_face(tmp_path: Path) -> None:
    path = tmp_path / "blank.png"
    cv2.imwrite(str(path), np.zeros((300, 300, 3), dtype=np.uint8))
    with pytest.raises(FaceAnalysisError):
        FaceAnalyzer().analyze(path)


def test_unreadable_image_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "bad.jpg"
    path.write_text("not an image", encoding="utf-8")
    with pytest.raises(FaceAnalysisError):
        FaceAnalyzer().analyze(path)

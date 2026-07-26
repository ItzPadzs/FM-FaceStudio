from pathlib import Path

from facestudio.matching.models import FaceDescriptor
from facestudio.matching.presets import DescriptorPresetStore


def test_preset_round_trip(tmp_path: Path) -> None:
    descriptor = FaceDescriptor(
        face_height_width_ratio=1.25,
        inter_eye_face_width_ratio=0.34,
        eye_line_face_height_ratio=0.39,
        mouth_line_face_height_ratio=0.76,
        face_shape="oval",
    )
    path = tmp_path / "preset.json"
    store = DescriptorPresetStore()
    store.save(descriptor, path)

    loaded = store.load(path)
    assert loaded == descriptor

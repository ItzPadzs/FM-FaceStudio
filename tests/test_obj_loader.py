from pathlib import Path

import pytest

from facestudio.mesh.obj_loader import ObjFormatError, load_obj


def test_load_triangle(tmp_path: Path) -> None:
    path = tmp_path / "triangle.obj"
    path.write_text(
        "v 0 0 0\n"
        "v 1 0 0\n"
        "v 0 1 0\n"
        "f 1 2 3\n",
        encoding="utf-8",
    )

    mesh = load_obj(path)
    assert mesh.vertex_count == 3
    assert mesh.face_count == 1
    assert mesh.edge_count == 3


def test_negative_obj_indices(tmp_path: Path) -> None:
    path = tmp_path / "negative.obj"
    path.write_text(
        "v 0 0 0\n"
        "v 1 0 0\n"
        "v 0 1 0\n"
        "f -3 -2 -1\n",
        encoding="utf-8",
    )
    assert load_obj(path).face_count == 1


def test_empty_obj_rejected(tmp_path: Path) -> None:
    path = tmp_path / "empty.obj"
    path.write_text("# empty\n", encoding="utf-8")
    with pytest.raises(ObjFormatError):
        load_obj(path)

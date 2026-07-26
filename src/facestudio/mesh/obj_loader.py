from __future__ import annotations

from pathlib import Path

from facestudio.mesh.model import MeshData, Vec3


class ObjFormatError(ValueError):
    pass


def _parse_index(token: str, vertex_count: int) -> int:
    raw = token.split("/", 1)[0]
    if not raw:
        raise ObjFormatError("Face contains an empty vertex index.")
    value = int(raw)
    if value == 0:
        raise ObjFormatError("OBJ indices cannot be zero.")
    index = value - 1 if value > 0 else vertex_count + value
    if index < 0 or index >= vertex_count:
        raise ObjFormatError(f"Vertex index {value} is out of range.")
    return index


def load_obj(path: Path) -> MeshData:
    vertices: list[Vec3] = []
    faces: list[tuple[int, ...]] = []
    edges: set[tuple[int, int]] = set()

    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        raise ObjFormatError(str(exc)) from exc

    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        parts = line.split()
        keyword = parts[0].lower()

        try:
            if keyword == "v":
                if len(parts) < 4:
                    raise ObjFormatError("Vertex requires x, y and z.")
                vertices.append(
                    Vec3(float(parts[1]), float(parts[2]), float(parts[3]))
                )
            elif keyword == "f":
                if len(parts) < 4:
                    raise ObjFormatError("Face requires at least three vertices.")
                face = tuple(
                    _parse_index(token, len(vertices))
                    for token in parts[1:]
                )
                faces.append(face)
                for position, start in enumerate(face):
                    end = face[(position + 1) % len(face)]
                    edges.add(tuple(sorted((start, end))))
            elif keyword == "l":
                if len(parts) < 3:
                    continue
                indices = [
                    _parse_index(token, len(vertices))
                    for token in parts[1:]
                ]
                for start, end in zip(indices, indices[1:]):
                    edges.add(tuple(sorted((start, end))))
        except (ValueError, ObjFormatError) as exc:
            raise ObjFormatError(
                f"Line {line_number}: {exc}"
            ) from exc

    if not vertices:
        raise ObjFormatError("The OBJ file contains no vertices.")

    return MeshData(
        source_path=path,
        vertices=tuple(vertices),
        edges=tuple(sorted(edges)),
        faces=tuple(faces),
    )

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math
import struct

from facestudio.hair.models import HairDescriptor


class HairSkinError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class HairMesh:
    positions: tuple[tuple[float, float, float], ...]
    uvs: tuple[tuple[float, float], ...]
    indices: tuple[int, ...]

    @property
    def vertex_count(self) -> int:
        return len(self.positions)

    @property
    def triangle_count(self) -> int:
        return len(self.indices) // 3


def read_fm26_hair_skin(path: str | Path) -> HairMesh:
    """Read the proven FM26 rigid/unweighted 12-byte/32-byte hair layout.

    Hair is intentionally read-only here.  The matcher never rewrites topology,
    normals, UVs or texture data.
    """

    path = Path(path)
    data = path.read_bytes()
    if len(data) < 12:
        raise HairSkinError(f"{path.name}: file too small")

    vertex_count, index_count, third = struct.unpack_from("<III", data, 0)
    if third != 0:
        raise HairSkinError(f"{path.name}: not an FM26 rigid/unweighted hair skin")
    if index_count % 3:
        raise HairSkinError(f"{path.name}: index count is not divisible by three")

    stride = 32
    expected = 12 + vertex_count * stride + index_count * 4
    if expected != len(data):
        raise HairSkinError(
            f"{path.name}: unsupported hair layout; expected {expected} bytes, got {len(data)}"
        )

    positions: list[tuple[float, float, float]] = []
    uvs: list[tuple[float, float]] = []
    for index in range(vertex_count):
        offset = 12 + index * stride
        x, y, z, _nx, _ny, _nz, u, v = struct.unpack_from("<8f", data, offset)
        if not all(math.isfinite(value) for value in (x, y, z, u, v)):
            raise HairSkinError(f"{path.name}: non-finite vertex data at {index}")
        positions.append((x, y, z))
        uvs.append((u, v))

    index_offset = 12 + vertex_count * stride
    indices = struct.unpack_from(f"<{index_count}I", data, index_offset) if index_count else ()
    if indices and max(indices) >= vertex_count:
        raise HairSkinError(f"{path.name}: triangle references vertex outside mesh")

    return HairMesh(tuple(positions), tuple(uvs), tuple(int(i) for i in indices))


def _occupancy_signature(
    points: tuple[tuple[float, float], ...],
    grid: int = 12,
) -> tuple[int, ...]:
    if not points:
        return tuple(0 for _ in range(grid * grid))
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)
    dx = max(x1 - x0, 1e-9)
    dy = max(y1 - y0, 1e-9)
    cells = [0] * (grid * grid)
    for x, y in points:
        ix = min(grid - 1, max(0, int((x - x0) / dx * grid)))
        iy = min(grid - 1, max(0, int((y - y0) / dy * grid)))
        cells[iy * grid + ix] = 1
    return tuple(cells)


def _component_count(vertex_count: int, indices: tuple[int, ...]) -> int:
    if vertex_count == 0:
        return 0
    parent = list(range(vertex_count))
    rank = [0] * vertex_count
    used = [False] * vertex_count

    def find(value: int) -> int:
        while parent[value] != value:
            parent[value] = parent[parent[value]]
            value = parent[value]
        return value

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra == rb:
            return
        if rank[ra] < rank[rb]:
            ra, rb = rb, ra
        parent[rb] = ra
        if rank[ra] == rank[rb]:
            rank[ra] += 1

    for offset in range(0, len(indices), 3):
        a, b, c = indices[offset : offset + 3]
        used[a] = used[b] = used[c] = True
        union(a, b)
        union(b, c)
        union(c, a)

    roots = {find(index) for index, is_used in enumerate(used) if is_used}
    isolated = sum(1 for is_used in used if not is_used)
    return len(roots) + isolated


def describe_hair_mesh(mesh: HairMesh) -> HairDescriptor:
    if not mesh.positions:
        raise HairSkinError("hair mesh contains no vertices")

    xs = [p[0] for p in mesh.positions]
    ys = [p[1] for p in mesh.positions]
    zs = [p[2] for p in mesh.positions]
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)
    z0, z1 = min(zs), max(zs)
    width = max(x1 - x0, 1e-9)
    height = max(y1 - y0, 1e-9)
    depth = max(z1 - z0, 1e-9)
    centroid_y = sum(ys) / len(ys)

    # Each projection is independently normalised.  This intentionally compares
    # hairstyle silhouette rather than absolute head scale/seat.
    front = _occupancy_signature(tuple((x, y) for x, y, _z in mesh.positions))
    side = _occupancy_signature(tuple((z, y) for _x, y, z in mesh.positions))
    top = _occupancy_signature(tuple((x, z) for x, _y, z in mesh.positions))

    outside = sum(
        1 for u, v in mesh.uvs if u < 0.0 or u > 1.0 or v < 0.0 or v > 1.0
    ) / max(1, len(mesh.uvs))

    return HairDescriptor(
        vertex_count=mesh.vertex_count,
        triangle_count=mesh.triangle_count,
        component_count=_component_count(mesh.vertex_count, mesh.indices),
        width_height_ratio=width / height,
        depth_height_ratio=depth / height,
        width_depth_ratio=width / depth,
        centroid_y_ratio=(centroid_y - y0) / height,
        front_occupancy=front,
        side_occupancy=side,
        top_occupancy=top,
        uv_outside_fraction=outside,
    )


def describe_hair_skin(path: str | Path) -> HairDescriptor:
    return describe_hair_mesh(read_fm26_hair_skin(path))


def describe_point_cloud(
    positions: list[tuple[float, float, float]] | tuple[tuple[float, float, float], ...],
) -> HairDescriptor:
    """Build a silhouette descriptor from foreign/source hair positions.

    This is the bridge for EA FC/PES importers: they can pass the already-decoded
    hairstyle point cloud without converting it into an FM hair file first.
    """

    points = tuple((float(x), float(y), float(z)) for x, y, z in positions)
    if not points:
        raise HairSkinError("source hair point cloud contains no vertices")
    dummy_uvs = tuple((0.5, 0.5) for _ in points)
    descriptor = describe_hair_mesh(HairMesh(points, dummy_uvs, ()))
    return HairDescriptor(
        vertex_count=descriptor.vertex_count,
        triangle_count=0,
        component_count=0,
        width_height_ratio=descriptor.width_height_ratio,
        depth_height_ratio=descriptor.depth_height_ratio,
        width_depth_ratio=descriptor.width_depth_ratio,
        centroid_y_ratio=descriptor.centroid_y_ratio,
        front_occupancy=descriptor.front_occupancy,
        side_occupancy=descriptor.side_occupancy,
        top_occupancy=descriptor.top_occupancy,
        uv_outside_fraction=0.0,
    )

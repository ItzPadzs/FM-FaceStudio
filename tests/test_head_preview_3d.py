from facestudio.ui.head_preview_3d import build_head_mesh


def test_head_mesh_contains_uv_mapped_triangles_and_edges() -> None:
    mesh = build_head_mesh(12, 8)

    vertex_count = (12 + 1) * (8 + 1)
    assert len(mesh.vertices) == vertex_count * 8
    assert len(mesh.triangle_indices) == 12 * 8 * 6
    assert len(mesh.line_indices) > 0
    assert max(mesh.triangle_indices) < vertex_count

    uv_values = [mesh.vertices[index] for index in range(6, len(mesh.vertices), 8)]
    vv_values = [mesh.vertices[index] for index in range(7, len(mesh.vertices), 8)]
    assert min(uv_values) == 0.0
    assert max(uv_values) == 1.0
    assert min(vv_values) == 0.0
    assert max(vv_values) == 1.0


def test_head_mesh_rejects_unusable_segment_counts() -> None:
    try:
        build_head_mesh(4, 4)
    except ValueError as exc:
        assert "at least 8 longitude" in str(exc)
    else:
        raise AssertionError("Expected a ValueError for an undersized mesh")

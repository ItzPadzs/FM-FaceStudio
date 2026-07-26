# FM FaceStudio

Open-source desktop tooling for researching, analysing and eventually generating Football Manager 2026 faces from a single photograph.

**Current release:** Sprint 4 — Mesh Explorer (`0.4.0-alpha.1`)

## Sprint 4 features

- Interactive software-rendered 3D wireframe viewport
- Wavefront OBJ loading
- Mouse rotation, zoom and panning
- Vertex, edge, face and bounds statistics
- Read-only binary inspection for unsupported files
- Double-click an indexed Asset Explorer result to open it
- Included demonstration OBJ under `examples/sample_head.obj`
- Dashboard sprint-label correction
- All Sprint 2 and Sprint 3 features retained

## Format support

Sprint 4 renders **Wavefront OBJ only**. Football Manager `.skin` and other proprietary formats are not claimed to be decoded. Those files open in inspection-only mode, showing safe file metadata and header bytes.

## Trying the viewport

1. Start FaceStudio.
2. Open **Mesh Explorer**.
3. Click **Open file…**.
4. Choose `examples/sample_head.obj`.
5. Drag to rotate, use the mouse wheel to zoom, and hold Shift while dragging to pan.

## Tests

```powershell
python -m pytest
```

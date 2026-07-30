# FaceStudio 3.2 — Interactive 3D Preview

FaceStudio can now display the generated texture on a lightweight OpenGL head proxy before export.

## Workflow

1. Open or create a project.
2. Upload and align the portrait.
3. Generate the UV texture.
4. Select **3D Preview** in the project toolbar.
5. Drag with the left mouse button to rotate.
6. Use the mouse wheel to zoom.
7. Adjust lighting or enable wireframe view to inspect coverage and seams.

## Safety and scope

The viewer is read-only. It does not resample, warp or rewrite the generated texture. The regular UV image is uploaded to the GPU and sampled on a generic review mesh.

The proxy is not an extracted Football Manager model and is not intended to reproduce a particular in-game head shape. Its purpose is fast inspection of texture orientation, broad facial placement, colour balance and seam behaviour.

## Controls

- **Drag:** rotate the head
- **Mouse wheel:** zoom
- **Wireframe:** inspect mesh and UV coverage
- **Lighting:** vary diffuse lighting strength
- **Reset View:** restore the default camera

## Requirements

The preview uses `QOpenGLWidget` and the OpenGL classes included with PySide6. A working desktop OpenGL driver is required. Projects and generation remain usable when the preview is not opened.

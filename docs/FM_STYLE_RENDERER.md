# FaceStudio 2.3 — FM Diffuse Style Renderer

FaceStudio 2.3 adds an appearance pass after the fixed 1024×1024 UV geometry stage.

The renderer is designed to reduce the photographic look of the transferred portrait while preserving the working Football Manager UV layout supplied by the donor texture.

## Pipeline

1. Select the closest working FM donor texture.
2. Map the portrait into the fixed FM UV coordinates.
3. Compress photographic highlights and lift deep shadows.
4. Build a low-frequency skin layer to reduce hard photo lighting.
5. Retain a restrained amount of facial detail.
6. Add deterministic low-amplitude diffuse grain.
7. Apply a final colour and saturation finish.
8. Export an exact 1024×1024 PNG.

## What this improves

- less harsh photographic lighting
- softer broad skin transitions
- reduced pasted-photo appearance
- more consistent diffuse-map contrast
- deterministic skin texture across repeated runs
- genuine style-stage preview frames in the desktop UI

## Accuracy boundary

This is a procedural style renderer, not a trained portrait-to-FM model. It does not claim to reproduce Sports Interactive's internal art pipeline. Its purpose is to create a visibly more game-texture-like baseline while keeping the fixed UV geometry stable.

The next major quality step remains a trained portrait-to-UV appearance model using reviewed paired examples.

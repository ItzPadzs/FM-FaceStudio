# FaceStudio 3.1 — Five-point portrait alignment

FaceStudio now collects five source-photo landmarks before generation:

1. left eye
2. right eye
3. nose tip
4. mouth centre
5. chin

The user clicks these points directly on the portrait. FaceStudio immediately renders a canonical 1024×1024 aligned preview. The alignment can be reset or corrected before it is accepted.

## Geometry rule

Only the uploaded portrait is rotated, scaled and translated. The donor UV texture is never geometrically transformed, so its eyes, nostrils, mouth cavity, ears and seams remain fixed.

## Project persistence

Each project stores:

- the original portrait path
- `alignment/aligned-portrait.png`
- five normalised landmark coordinates
- the generated UV texture

Reopening the project restores the aligned portrait and allows the alignment editor to be opened again.

## Desktop workflow

```text
Upload portrait
      ↓
Click five landmarks
      ↓
Review canonical preview
      ↓
Use Alignment
      ↓
Generate through existing UV-safe pipeline
```

## Current boundary

This milestone is UI-assisted and deterministic. Automatic MediaPipe landmark inference remains optional future work. Manual placement is retained as the reliable fallback and calibration tool.

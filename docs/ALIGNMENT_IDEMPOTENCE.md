# FaceStudio 2.5 — Alignment idempotence

FaceStudio must never move facial features when the uploaded image is already a correctly aligned Football Manager UV texture.

## Failure reproduced

Passing a working 1024×1024 FM texture back through the earlier pipeline caused the crop and fixed-UV warp to run again. The second transform produced doubled mouths, nostrils and facial edges.

## New guard

Before trained inference or the procedural fallback runs, FaceStudio now compares the uploaded square texture with the selected donor prior using a low-resolution RGB mean absolute error measurement.

The secondary alignment stage is skipped only when all of the following are true:

- the upload is square
- it is at least 512×512
- it is visually near-identical to the selected canonical UV texture

Normal photographs and unrelated square images continue through the active generator.

## Expected identity test

Input: a working FM UV texture also selected as the donor.

Expected result:

- `alignment_bypassed: true`
- mean absolute error close to zero
- no second crop or warp
- output geometry and feature locations identical to the input
- exact 1024×1024 PNG export

The guard is intentionally conservative. It fixes the demonstrated double-alignment bug without pretending to recognise every possible FM UV texture from dimensions alone.

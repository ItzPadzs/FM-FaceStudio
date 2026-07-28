# FaceStudio 2.2 — Fixed UV Geometry

FaceStudio 2.2 changes the deterministic generator from separate rectangular facial transfers to one continuous facial surface placed into a canonical Football Manager diffuse-texture layout.

## Output contract

Every generated texture is written as:

```text
1024 × 1024 PNG
```

The fixed geometry profile records stable normalised positions for:

- full inner-face bounds
- left and right eye centres
- nose centre
- mouth centre
- chin centre

The donor texture is first normalised to the canonical atlas size. The portrait then fills one continuous forehead/cheek/jaw mask inside those fixed coordinates. Small eye, nose and mouth detail passes operate only within the same surface.

## Generation stages

```text
portrait + selected working FM donor
                 |
                 v
       frontal portrait normalisation
                 |
                 v
        canonical 1024 UV preparation
                 |
                 v
        unified face-surface placement
                 |
                 v
      multi-pass boundary feathering
                 |
                 v
       local eyes/nose/mouth refinement
                 |
                 v
          complete 1024x1024 PNG
```

## Why this improves the previous prototype

The earlier regional engine transferred forehead, mid-face and jaw as independent patches. That produced visible stacked seams and inconsistent facial width.

The new engine:

- uses one broad forehead-to-chin mask
- covers both cheeks continuously
- tapers through the jaw and chin
- keeps the source face aligned to one fixed destination rectangle
- uses nested blend boundaries to soften the face edge
- guarantees the final FM texture dimensions
- records the fixed anchors in generation provenance

## Accuracy boundary

This release establishes deterministic UV placement and a coherent face surface. It does not claim dense landmark detection or learned reconstruction. A frontal portrait cannot provide hidden scalp, ear, side-head or neck detail, so the selected working donor remains the prior for those regions.

The next quality milestone is automatic landmark detection and piecewise mesh warping inside this fixed UV contract. That future engine can replace the conservative portrait crop without changing the output coordinates, desktop workflow or export format.

# FaceStudio 3.0 — Project workspace

FaceStudio 3.0 begins the move from a one-shot generator to a persistent creation workspace.

## Added in this milestone

- named FaceStudio projects
- `facestudio-project-v1` JSON manifests
- saved portrait, donor, generated texture and diagnostic references
- project-owned output and diagnostics folders
- New Project, Open Project and Save Project controls
- automatic portrait persistence after import
- restoration of portrait and generated-texture previews
- FaceStudio 3.0 window launched by default

## Project structure

```text
projects/
└── Player Name/
    ├── project.json
    ├── output/
    └── diagnostics/
```

The manifest records the project name, source portrait, selected donor texture, generated texture, mask profile, colour strength, diagnostics and timestamps.

## Current boundary

This is the first FaceStudio 3.0 milestone. It does not yet add the interactive landmark editor, before/after slider, painted UV masks, quality scoring or 3D preview. The existing generation interface remains available underneath the new project bar while those systems are developed incrementally.

## Safety rule

Project persistence does not alter the UV pipeline. Source alignment may transform the portrait, but donor UV geometry and protected facial regions remain fixed.

## Verification

```bash
python -m pip install -e ".[dev]"
python -m pytest
fm-facestudio
```

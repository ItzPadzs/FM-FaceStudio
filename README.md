# FM FaceStudio

Open-source desktop tooling for researching, analysing and eventually generating Football Manager 2026 faces from a single photograph.

**Current release:** Sprint 7 — Descriptor Studio (`0.7.0-alpha.1`)

## Sprint 7 features

- Interactive sliders for all current descriptor measurements
- Live comparison with the original analysis
- Load a second descriptor preset for side-by-side comparison
- Save edited descriptor presets
- Radar-chart visualisation
- Live overall similarity score
- Per-component similarity breakdown
- Plain-language explanations for every matching component
- Existing project, scanning, mesh, analysis and matching features retained

## Using Descriptor Studio

1. Open a project with completed Face Analysis.
2. Open **Descriptor Studio**.
3. Move the sliders to explore descriptor changes.
4. Review the live radar chart and similarity table.
5. Save the edited values as a separate JSON preset.
6. Load another preset to compare it side by side.

Descriptor Studio does not overwrite the original `analysis.json`.

## Tests

```powershell
python -m pytest
```

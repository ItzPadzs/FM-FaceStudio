# FM FaceStudio

Open-source desktop tooling for researching, analysing and eventually generating Football Manager 2026 faces from a single photograph.

**Current release:** Sprint 5 — Face Analysis (`0.5.0-alpha.1`)

## Sprint 5 features

- OpenCV frontal-face detection
- Eye detection where image quality allows
- Mouth-region detection where image quality allows
- Proportional nose, chin and forehead anchors
- Normalised facial landmark coordinates
- Face proportion measurements
- Broad face-shape descriptor
- Analysis confidence and detection-source labels
- Landmark overlay preview
- Automatic `analysis.json` and `preview.png` storage inside each project
- Background analysis so the interface remains responsive

## Important limitation

This is an analysis foundation, not a biometric identification system. Haar cascades work best with a clear, well-lit, front-facing portrait. Green markers are detected features; amber markers are explicitly labelled proportional estimates. Face-shape categories are broad geometric descriptors rather than definitive classifications.

## Using Face Analysis

1. Create or open a project.
2. Import a clear source photograph on the **Project** page.
3. Open **Face Analysis**.
4. Click **Analyse photograph**.
5. Review the overlay and descriptor.
6. Find saved results in the project folder as `analysis.json` and `preview.png`.

## Install/update

Run `INSTALL_AND_OPEN.bat` once after updating because Sprint 5 adds OpenCV.

## Tests

```powershell
python -m pytest
```

# FM FaceStudio

Open-source desktop tooling for researching, analysing and eventually generating Football Manager 2026 faces from a single photograph.

**Current release:** Sprint 6 — Face Matcher (`0.6.0-alpha.1`)

## Sprint 6 features

- Converts project analysis into a reusable numerical face descriptor
- Weighted similarity engine
- Ranked top-10 candidate results
- Per-component similarity scores
- Sample descriptor catalogue included for transparent testing
- Custom JSON catalogue selection
- Automatic `matches.json` storage inside the project
- Background matching so the interface remains responsive
- Existing project, asset, mesh and face-analysis features retained

## Important limitation

Sprint 6 validates the matching architecture against FaceStudio descriptor records. It does **not** claim to identify or decode Football Manager proprietary head meshes. Connecting real FM assets requires independently validated metadata or a lawful conversion pipeline.

## Using Face Matcher

1. Create or open a project.
2. Import and analyse a frontal photograph.
3. Open **Face Matcher**.
4. Click **Find closest matches**.
5. Review the ranked results.
6. Find the saved output at `matches.json` inside the project folder.

A sample catalogue is included at:

```text
data/sample_face_catalogue.json
```

## Tests

```powershell
python -m pytest
```

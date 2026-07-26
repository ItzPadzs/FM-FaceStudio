# FM FaceStudio

Open-source desktop tooling for researching, analysing and eventually generating Football Manager 2026 faces from a single photograph.

**Current release:** Sprint 2 — Projects (`0.2.0-alpha.1`)

## Working features

- Create a structured `.facestudio` project folder
- Open and save projects
- Import and locally copy a source photograph
- Project notes and player name
- Recent-project dashboard
- Configurable autosave
- Unsaved-change protection
- Persistent settings
- FM26 installation detection
- Dark and light themes
- Read-only safety policy

## Project structure

```text
Player Name.facestudio/
├── project.json
├── source/
│   └── source_photo.jpg
└── generated/
```

## Start on Windows

1. Extract the ZIP.
2. Double-click `INSTALL_AND_OPEN.bat`.
3. Use `RUN.bat` after the first setup.

## Tests

```powershell
python -m pytest
```

The application does not modify Football Manager files.

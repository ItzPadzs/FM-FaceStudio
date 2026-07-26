# FM FaceStudio

Open-source desktop tooling for researching, analysing and eventually generating Football Manager 2026 faces from a single photograph.

**Current release:** Sprint 3 — Asset Database (`0.3.0-alpha.1`)

## Sprint 3 features

- Read-only folder scanner
- Background scanning to keep the application responsive
- Local SQLite asset database
- Search by filename or relative path
- Filter by cautious inferred asset category
- Filter by file extension
- File size, modification time and relative-path display
- Scan cancellation
- Existing Sprint 2 project workflows and autosave

## Important safety note

The scanner reads file metadata only. It does not modify, decode or export Football Manager files. Asset categories are inferred from filenames, folders and extensions and are not claims about proprietary file formats.

## Start on Windows

Run `INSTALL_AND_OPEN.bat` after copying the Sprint 3 files into your local repository. Existing environments can usually be started with `RUN.bat`.

## Tests

```powershell
python -m pytest
```

# Contributing

```powershell
py -3.11 -m venv .venv
.venv\Scripts\activate
pip install -e .[dev]
pytest
python launcher.py
```

Keep game-file handling read-only unless backup and restore support is part of the tested change.
Use type hints and add tests for non-UI behaviour.

# DylanFM compatibility adapter

FM-FaceStudio can consume the observable JSON files produced by DylanFM Player Radar without loading, modifying or redistributing DylanFM binaries.

## Observed public outputs

The supplied DylanFM package contains `DylanFM.PlayerRadar.dll`. Its embedded diagnostic strings reference these file names:

- `active-player.json`
- `ui-probe.json`
- `native-selection-probe.json`
- `player-report-*.json`

The adapter reads only the first three JSON outputs. It accepts common field variants such as `playerId`, `player_id`, `uid`, `playerName` and `player_name`.

## Run

Keep Football Manager and DylanFM Player Radar running, then execute from the FM-FaceStudio repository:

```powershell
python tools\run_dylanfm_adapter.py --fm-root "C:\Program Files (x86)\Steam\steamapps\common\Football Manager 26"
```

If DylanFM writes its JSON somewhere unexpected, provide the folder explicitly:

```powershell
python tools\run_dylanfm_adapter.py `
  --fm-root "C:\Program Files (x86)\Steam\steamapps\common\Football Manager 26" `
  --source-root "C:\path\to\DylanFMPlayerRadar"
```

Open a player profile in FM. A successful detection is republished to:

```text
%LOCALAPPDATA%\FM-FaceStudio\bridge\selected-player.json
```

Adapter diagnostics are written to:

```text
%LOCALAPPDATA%\FM-FaceStudio\bridge\dylanfm-adapter-status.json
```

## Boundary

This compatibility layer is a file-format adapter. It does not decompile, patch, reflect over, bundle or redistribute `DylanFM.PlayerRadar.dll` or `HeadHunter2.dll`. The third-party plugin remains responsible for producing its own output files.

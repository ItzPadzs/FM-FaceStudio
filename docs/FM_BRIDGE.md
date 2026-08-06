# FM FaceStudio Bridge 0.1

The bridge is a small BepInEx 6 IL2CPP plugin plus a Python desktop client. It deliberately exchanges JSON beneath the current user's LocalAppData directory instead of writing runtime state into `Program Files (x86)`. This avoids the `UnauthorizedAccessException` seen when a plugin attempts to use protected game-installation paths.

## Transport directory

```text
%LOCALAPPDATA%\FM-FaceStudio\bridge\
├── commands\
├── processing\
├── responses\
├── status.json
└── selected-player.json
```

The BepInEx plugin refreshes `status.json` every second. The desktop application treats the bridge as connected only while that heartbeat is fresh.

## Build and install

Install the .NET 6 SDK, close Football Manager, and run PowerShell from the repository root:

```powershell
.\bridge\build-and-install.ps1 `
  -FmRoot "C:\Program Files (x86)\Steam\steamapps\common\Football Manager 26" `
  -Install
```

The script compiles and installs:

```text
BepInEx\plugins\FMFaceStudioBridge\FMFaceStudioBridge.dll
```

Restart Football Manager and verify that `BepInEx\LogOutput.log` contains:

```text
FM FaceStudio Bridge 0.1.0 loading
Bridge directory: C:\Users\<user>\AppData\Local\FM-FaceStudio\bridge
```

## Protocol

### Ping

Write to `commands/<id>.json`:

```json
{
  "id": "example",
  "type": "ping"
}
```

The plugin writes `responses/example.json` with `success: true` and `message: "pong"`.

### Publish a player selection

```json
{
  "id": "example-player",
  "type": "publish-player",
  "player": {
    "id": 37055843,
    "name": "Matthijs de Ligt",
    "club": "Manchester United",
    "nation": "Netherlands",
    "source": "manual-test"
  }
}
```

The validated selection is atomically written to `selected-player.json`.

## Current boundary

Version 0.1 proves installation, heartbeat, permissions-safe IPC, command handling and desktop-side parsing. It does **not yet read Football Manager's internal selected-player object**. That requires a supported selection adapter or a small compatibility layer for the exact FM26/BepInEx interfaces in use. The existing third-party DylanFM Player Radar proves that selection data is available, but this repository does not contain its source or a documented public API, so the bridge must not guess at or hard-code that private implementation.

The next milestone is one of:

1. a public Player Radar adapter, if its author exposes an event/API; or
2. an independent FM26 UI selection probe developed and tested against legally available local assemblies.

Until then, `publish-player` provides a deterministic end-to-end test of the transport and FaceStudio workflow.

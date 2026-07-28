# FaceStudio 2.1 — Self-Contained Asset Setup

Users no longer select or manage `donor-asset-index.json`.

## First run

1. Upload a portrait.
2. When prompted, choose a folder containing working FM head textures.
3. FaceStudio scans the folder, builds its own local index and remembers the source.
4. Generation starts automatically.

The application-owned index is stored under the FaceStudio application-data directory in `donor-library/index`. On later launches it is detected and loaded automatically.

The **Import Facepack / Donor Folder** control can be used to replace or rebuild the local donor library. Source texture files remain in their original folder; FaceStudio stores only index metadata and generated thumbnails.

## Important limitation

FaceStudio 2.1 removes manual JSON setup, but the current regional-transfer engine still requires legal, locally supplied FM-compatible donor textures. This release does not bundle third-party facepack artwork or claim that the deterministic engine can generate a complete native-style texture without donor assets.

# FaceStudio 2.0 Beta — Live Generation Overhaul

This release replaces the old Alpha 11 window with a production-style dashboard based on the approved FaceStudio concept.

## Visible workflow

1. Choose the existing `donor-asset-index.json` once.
2. Upload one front-facing portrait.
3. FaceStudio ranks the donor library automatically.
4. The active regional-transfer engine emits real PNG previews.
5. The main UV preview and bottom thumbnail strip update from those engine files.
6. The complete FM UV is exported to the application data output folder.

## Interface overhaul

- dark professional sidebar
- prominent one-click upload action
- nine-stage pipeline display
- full-width progress bar and live stage message
- source portrait and generated UV shown side by side
- seven-frame generation filmstrip
- donor-index and engine status
- automatic output-folder access
- immediate generation after portrait upload

## Honest progress

The preview strip does not reveal a finished image cosmetically. Each populated thumbnail comes from the `RegionalTransferEngine` progress callback and is written during generation. Donor selection, alignment, regional transfer and final output therefore show distinct engine states.

## Current quality boundary

The active engine remains deterministic. It performs donor selection, colour matching and regional soft-mask transfer; it is not a trained portrait-to-UV network. The overhaul makes the real process visible and gives future landmark or model engines the same professional interface without pretending they already exist.

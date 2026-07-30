# FaceStudio 2.7 — Portrait alignment and mask profiles

This milestone adds the missing bridge between a normal player photograph and the UV-safe skin-transfer stage introduced in 2.6.

## Rules

- Alignment transforms the source portrait only.
- Donor UV geometry is never warped.
- Eyes, nostrils, mouth cavity and ears remain protected during compositing.
- Automatic landmark libraries are optional rather than mandatory application dependencies.

## Components

- `alignment.py`: landmark contract, manual/UI detector and canonical similarity transform.
- `portrait_pipeline.py`: portrait alignment followed by deterministic skin transfer.
- `profiles.py`: validated JSON mask-profile loader.
- `templates/profiles/`: initial FM, EA FC and eFootball profile placeholders.

## Current limitation

The MediaPipe adapter is an explicit integration boundary, not a completed detector. The first usable desktop workflow should collect five landmarks through UI clicks, while a later milestone can configure an optional MediaPipe Tasks model.

The EA FC and eFootball rectangles are provisional and must be calibrated against legally usable templates before production export is enabled.

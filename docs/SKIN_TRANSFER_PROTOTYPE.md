# FaceStudio 2.6 — UV-safe skin-transfer prototype

This milestone adds a deterministic surface-transfer stage for already aligned portrait and donor images.

## Design rule

The prototype may change colour and visible skin detail, but it must not move UV geometry. Eyes, nostrils, the mouth cavity and ears are protected so the donor texture remains exact in animation-sensitive areas.

## Pipeline

1. Read the aligned portrait and donor texture.
2. Match the portrait dimensions to the donor canvas.
3. Extract a conservative skin candidate and confidence mask.
4. Build protected-region masks for eyes, nostrils, mouth and ears.
5. Combine skin confidence with protection masks.
6. Calculate a robust median colour shift.
7. Composite matched surface pixels over the donor.
8. Export the final PNG and optional diagnostics.

## Diagnostic outputs

- `skin_candidate.png`
- `candidate_mask.png`
- `protection_mask.png`
- `confidence_map.png`
- `colour_matched.png`
- `composite_preview.png`

## Current limitations

- The input portrait must already be aligned to the donor UV.
- The bootstrap skin mask uses deterministic RGB relationships rather than a learned face parser.
- Colour matching currently uses robust channel medians. The interface is prepared for a later OpenCV CIE Lab implementation.
- Protected regions use conservative normalised FM defaults and will later become donor-profile data.

## Next milestone

Connect landmark-based portrait alignment and donor-specific mask profiles, then expose the prototype through the desktop UI with a before/after and confidence-map preview.

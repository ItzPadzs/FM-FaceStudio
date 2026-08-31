# FM-FaceStudio Hair Matcher + Browser update

This update adds a native-FM hair recommendation and manual-selection layer without changing the existing face conversion engines.

## What is included

- **Automatic Best Match**: ranks the complete native FM hair library against the source hairstyle using front, side and top silhouette signatures plus scale-independent proportions. Topology/detail counts are deliberately only a small secondary signal because the FM26 corpus contains multiple valid structural families.
- **Choose Manually**: searchable donor list with player/UID, match score, proven status, contract completeness, vertex/triangle counts and a three-view silhouette preview.
- **Compare Top 4**: side-by-side Front / Side / Top previews for the leading candidates (or up to four manually selected candidates).
- **Use FM Native Player Hair** and **No Custom Hair** modes.
- **Mark Proven / Unmark Proven**: successful in-game donor hairs are remembered in `hair-proven.json`. Proven status gives only a small confidence bonus; it cannot make a visually poor hairstyle outrank a substantially better silhouette.
- **Byte-locked Hair Test Package** export: donor `.skin`, diffuse and exactly the normal-map filenames the donor supplies are copied unchanged under the target UID. SHA-256 is verified after copying.
- **EA FC / PES converter hook**: foreign hair geometry can be converted to a `HairDescriptor` with `describe_point_cloud(...)`, then ranked through `HairMatchingService.rank_descriptor_against_library(...)` without first creating an FM hair file.

## Native FM contract rules

The matcher never assumes that a working hair should have UVs inside 0–1, one particular winding direction, binary alpha, one texture size, blue=255 normals, or both normal-map filenames. It does **not** rewrite geometry, UVs, winding, alpha or normal maps during selection.

`_hair_nrm.png` and `_hair2_nrm.png` are preserved as separate semantic assets. No compatibility alias is generated.

## Ranking weights

- Front silhouette: 30%
- Side silhouette: 24%
- Top silhouette: 12%
- Width / height: 11%
- Depth / height: 9%
- Width / depth: 5%
- Vertical mass: 4%
- Structural similarity: 5%

These are intentionally visual-first. They can be tuned later from in-game proven/failed selections.

## Converter integration

Once an EA FC or PES/eFootball importer has decoded and seated the source hairstyle point cloud into the same orientation used for preview, the conversion path can call:

```python
from facestudio.hair.skin import describe_point_cloud
from facestudio.hair.service import HairMatchingService

source_descriptor = describe_point_cloud(source_hair_positions)
service = HairMatchingService(cache_path=cache_path, proven_path=proven_path)
results = service.rank_descriptor_against_library(
    source_descriptor,
    fm_hair_library,
    limit=25,
)
best = results[0] if results else None
```

The user can accept `best`, choose another ranked candidate manually, keep FM's native player hair, or export with no custom hair.

## Validation

Synthetic regression tests cover:

1. FM26 rigid/unweighted hair parsing and visual ranking.
2. Exact preservation of `_hair2_nrm` without inventing `_hair_nrm`.
3. Cross-UID package export with byte-identical donor assets.

The update passed Python `compileall` and the current regression suite (`3 passed`). In-game visual approval remains the final authority for marking a donor/combination as proven.

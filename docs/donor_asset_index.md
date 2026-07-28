# Donor Asset Index

Alpha 12.1 adds a deterministic donor-library foundation for the portrait-to-FM pipeline.

## Build an index

```bash
fm-facestudio-donors index \
  "C:/path/to/head-pack" \
  "C:/path/to/extra-assets" \
  --output "C:/FaceStudio/donor-index" \
  --names "C:/FaceStudio/player-names.csv"
```

The optional name map may be JSON (`{"317312": "Player Name"}`) or CSV with `id`/`uid`/`donor_id` and `name`/`player_name` columns.

The command writes:

```text
donor-index/
├── donor-asset-index.json
└── face-thumbnails/
    ├── 317312.png
    └── ...
```

Source assets are referenced in place and are not duplicated. The index separates diffuse head textures, geometry, hair, beard and eye assets where folder or file naming makes that classification reliable.

## Rank donors

```bash
fm-facestudio-donors match portrait.png \
  --index "C:/FaceStudio/donor-index/donor-asset-index.json" \
  --limit 12
```

The current matcher is a deterministic visual baseline based on a repeatable face crop and compact colour/structure descriptor. It is intended to provide useful initial candidates and a stable dataset foundation. It is not claimed to be a trained facial-recognition or identity model.

## Next integration

The application can use the resulting index to show named donor thumbnails, automatically select a UV/style prior, retain separate hair and beard choices, and record accepted matches as reviewed training examples for the portrait-to-UV model.

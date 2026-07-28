# FaceStudio 2.4 — Trained portrait-to-UV workflow

FaceStudio now contains a real trainable image-to-image backend. It does not include fabricated weights or claim that an untrained network produces useful textures.

## Dataset contract

Create a folder containing reviewed portrait/texture pairs and a `pairs.json` file:

```json
[
  {"portrait": "portraits/player-001.png", "uv": "uv/player-001.png"},
  {"portrait": "portraits/player-002.png", "uv": "uv/player-002.png"}
]
```

Each `uv` image must be a verified Football Manager-compatible 1024×1024 texture for the same person shown in the paired portrait. Do not pair unrelated public portraits with donor textures: the network would learn donor identity rather than portrait conversion.

## Install training support

```bash
python -m pip install -e ".[training]"
```

## Train

```bash
fm-facestudio-train DATASET_FOLDER \
  --output "$LOCALAPPDATA/FM-FaceStudio/models/portrait-uv" \
  --epochs 100 \
  --batch-size 2 \
  --image-size 512
```

Training writes:

- `portrait-uv-latest.pt`
- `model-manifest.json`

FaceStudio discovers those files automatically in its application-data `models/portrait-uv` directory. `FACESTUDIO_MODEL_DIR` can override the location.

## Runtime behaviour

When valid weights are installed, the desktop reports `Trained portrait-to-UV model ACTIVE` and uses neural inference. Without weights, it clearly labels the old procedural renderer as a prototype fallback.

## Important limitation

The code is now capable of training and running a model, but useful output still depends on a sufficiently large, accurately paired and legally usable dataset. The repository intentionally contains no third-party player imagery or Football Manager artwork and no pretend model checkpoint.

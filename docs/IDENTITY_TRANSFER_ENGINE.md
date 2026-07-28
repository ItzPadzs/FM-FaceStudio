# Alpha 13.0.0 — Identity Transfer Engine

Alpha 13 introduces a stable, model-agnostic generation boundary for FM FaceStudio.

## Pipeline

```text
portrait + selected donor + settings
                 |
                 v
          EngineRegistry
                 |
       selected implementation
                 |
                 v
       complete FM UV PNG
       + stages + provenance
```

The desktop application can now depend on one request/result contract instead of being tied to a particular compositor or machine-learning framework.

## Core API

```python
from pathlib import Path
from facestudio.ai import EngineRegistry, GenerationRequest

request = GenerationRequest(
    portrait=Path("portrait.png"),
    donor_texture=Path("donor.png"),
    output=Path("output/head.png"),
    donor_id="12345",
    donor_name="Selected donor",
)

result = EngineRegistry().generate(
    request,
    lambda percent, stage, preview: print(percent, stage, preview),
)
```

`GenerationResult` records the output path, engine name, donor identity, progressive stages and engine-specific metadata.

## Included engines

### `donor-baseline`

A safe integration baseline. It validates the portrait and donor, emits progressive events and exports the selected donor UV unchanged.

It does **not** transfer portrait identity and its result metadata explicitly records that boundary. This prevents a copied donor or deterministic compositor from being misrepresented as learned generation.

### `portrait-to-uv-model`

An adapter around the Alpha 12 `PortraitToUVModel` runtime. It becomes available only when a valid model manifest and declared weights are installed. Actual ONNX/Torch execution remains intentionally unavailable until real exported weights and the matching inference adapter exist.

## Engine extension

A new engine supplies:

- a unique `name`
- `available`
- `status_message`
- `generate(request, progress)`

It can then be registered without changing the caller:

```python
registry = EngineRegistry()
registry.register(MyOnnxEngine(model_directory))
```

## Reviewed training capture

`TrainingCapture` stores an explicit generation record containing:

- portrait path
- selected donor and donor ID
- generation settings
- engine and progressive stages
- generated texture
- optional manually edited final texture
- approval state and reviewer notes

Images are never collected automatically. Capture must be invoked deliberately, and `copy_assets=True` is required to copy images into the review directory.

The record format is:

```text
facestudio-generation-record-v1
```

These records can later be filtered to approved examples and converted into model-training or evaluation datasets.

## Accuracy boundary

Alpha 13 is the generation-platform release, not a claim that trained identity transfer already exists. It supplies the interchangeable engine contract, progressive output, provenance and reviewed-example capture. The included baseline preserves the donor unchanged; genuine portrait-to-FM transformation still requires reviewed training data, trained weights and a real inference implementation.

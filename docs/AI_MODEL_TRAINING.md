# Portrait-to-FM UV model training

Alpha 12 establishes the data and runtime contracts needed for a real portrait-to-UV generator.

## Required paired data

Each identity needs two files with the same filename stem:

```text
portraits/12345.jpg
uv_textures/12345.png
```

The portrait should be a clear frontal image. The UV texture must be the verified 1024×1024 texture that represents the same person in the target FM/BepInEx layout.

`PairedDatasetBuilder` scans both folders, creates `facestudio-portrait-uv-pairs-v1`, and reports missing counterparts. Unpaired or ambiguous files are not silently included.

## Model package

An exported model folder must contain:

```text
models/fm-facegen/
  model.json
  model.onnx
```

Example `model.json`:

```json
{
  "format": "facestudio-portrait-to-uv-model-v1",
  "model_name": "FM FaceGen",
  "version": "0.1.0",
  "weights": "model.onnx",
  "input_size": 512,
  "output_size": 1024,
  "backend": "onnx"
}
```

## Accuracy boundary

This update does not ship trained weights. It prepares verified training pairs and a strict runtime boundary so the application can later load a real exported model. The existing template-fitting generator remains separate and must not be presented as learned portrait-to-UV generation.

## Next milestone

1. Collect and review paired portraits and final UV textures.
2. Split by identity into training, validation and test sets.
3. Train an image-to-image model with identity, landmark and UV-layout supervision.
4. Export validated weights.
5. Add the matching inference adapter and connect live preview frames to actual model output.

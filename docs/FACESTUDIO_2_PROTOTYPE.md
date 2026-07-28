# FaceStudio 2.0 — End-to-End Prototype

This release joins the donor index and generation engine into one runnable pipeline that produces a visibly changed FM UV texture.

## Run it

```bash
python -m pip install -e .
fm-facestudio-2 portrait.png \
  --index "C:/FaceStudio/donor-index/donor-asset-index.json" \
  --output "C:/FaceStudio/output/generated.png"
```

The command:

1. reads the uploaded portrait;
2. ranks the indexed donor library;
3. automatically selects the closest baseline donor;
4. preserves the donor's FM UV atlas structure;
5. colour-matches the portrait face to the donor;
6. transfers forehead/eyes, nose/cheeks and mouth/jaw through separate soft masks;
7. writes progressive preview PNGs beside the output;
8. exports a complete PNG texture.

## What progress should now be visible

Unlike the donor baseline, `regional-transfer-v1` uses portrait pixels and changes the selected donor texture. The progress callbacks expose donor selection and each transferred region, allowing the desktop workflow to display the build as it happens.

## Accuracy boundary

This is the first end-to-end visual prototype, not the final quality target. It uses deterministic crops and masks rather than detected landmarks or a trained portrait-to-UV model. It will provide visible progress and a concrete comparison point, but difficult poses, expressions, lighting and inaccurate portrait framing can still produce weak alignment.

The output should now be judged directly: source portrait, selected donor and generated UV can be compared for every test case. Those comparisons determine whether the next work improves alignment, regional masks or learned inference.

# Dataset

This directory contains the pinned, synthetic reference snapshot used by the
demonstration.

## Reference parameters

- generator version: `0.1.0`
- seed: `2026`
- logical generation time: `2026-01-01T00:00:00Z`
- GPU models: `GPU-A`, `GPU-B`, `GPU-C`
- test cases: `TC-001` through `TC-010`
- normal samples per supported test/GPU pair: `30`
- sparse confidence case: `TC-010` on `GPU-C`, with `5` samples
- total runs: `545`

The sparse pair is intentional. A later rule will require more than five
samples, allowing the checker to demonstrate `insufficient-data` rather than
inventing a value.

## Artifacts

- `runs.json` contains measured status, duration, iteration count, and time.
- `capabilities.json` contains GPU capabilities and test requirements.
- `manifest.json` pins both source files by byte length and SHA-256 digest and
  identifies the combined snapshot.

## Reproduction

```powershell
python -m vgpu_catalog.dataset --output dataset
python -m vgpu_catalog.validation dataset
```

The second command must return `"valid": true` with an empty issue list.


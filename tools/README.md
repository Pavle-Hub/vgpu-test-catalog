# Tools

- `gen_dataset.py` is a thin CLI wrapper around the deterministic generator.
- `validate_dataset.py` validates schemas, references, hashes, timestamps, seed,
  and snapshot identity.
- `derive_catalog.py` validates both inputs and deterministically calculates the
  complete expected state of all derived catalog fields.

The equivalent installed commands are `generate-dataset` and
`validate-dataset`, and `derive-catalog-data`. The module form is also supported
and is used in the repository documentation because it works consistently
across shells.


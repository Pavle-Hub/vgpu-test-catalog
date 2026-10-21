# Tools

- `gen_dataset.py` is a thin CLI wrapper around the deterministic generator.
- `validate_dataset.py` validates schemas, references, hashes, timestamps, seed,
  and snapshot identity.
- `derive_catalog.py` validates both inputs and deterministically calculates the
  complete expected state of all derived catalog fields.
- `catalog_check.py` exposes read-only `--check` and local mechanical `--write`
  modes with structured JSON output and meaningful process exit codes.
- `run_metrics_mcp.py` starts the read-only measurement tools server over stdio.
- `run_env_mcp.py` starts the read-only capability resources server over stdio.

The equivalent installed commands are `generate-dataset` and
`validate-dataset`, `derive-catalog-data`, `catalog-check`, `metrics-mcp`, and
`env-mcp`. The module form is also supported and is used in the repository
documentation because it works consistently across shells.


# Tools

- `check_demo.py` checks local demo readiness without agents, network or writes.
- `run_dashboard.py` serves the local read-only evidence dashboard.
- `../Start-Dashboard.cmd` runs the preflight and dashboard from its own project directory.

- `gen_dataset.py` is a thin CLI wrapper around the deterministic generator.
- `validate_dataset.py` validates schemas, references, hashes, timestamps, seed,
  and snapshot identity.
- `derive_catalog.py` validates both inputs and deterministically calculates the
  complete expected state of all derived catalog fields.
- `catalog_check.py` exposes read-only `--check` and local mechanical `--write`
  modes with structured JSON output and meaningful process exit codes.
- `run_metrics_mcp.py` starts the read-only measurement tools server over stdio.
- `run_env_mcp.py` starts the read-only capability resources server over stdio.
- `../eval/inject_faults.py` generates checker suites and manages recorded agent
  experiments without treating generated results as source files.

The equivalent installed commands are `generate-dataset` and
`validate-dataset`, `derive-catalog-data`, `catalog-check`, `metrics-mcp`, and
`env-mcp`, plus `evaluate-catalog` for evaluation. The module form is also
supported and is used in the repository documentation because it works
consistently across shells.


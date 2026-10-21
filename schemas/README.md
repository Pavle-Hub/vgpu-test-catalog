# Dataset schemas

The schemas use JSON Schema Draft 2020-12 and define the structural contract
shared by the generator, MCP servers, deterministic checker, and evaluation
tools.

## Files

- `runs.schema.json` validates the synthetic measurement records.
- `capabilities.schema.json` validates GPU capabilities and test requirements.
- `manifest.schema.json` validates snapshot identity and artifact provenance.
- `rules.schema.json` validates the declarative derivation and ownership
  contract used by both the catalog writer and checker.
- `catalog-derived.schema.json` validates each hidden machine-readable Markdown
  block, including values, status, formula, timestamp, and snapshot hash.

## Cross-file invariants

JSON Schema validates individual documents. The deterministic dataset validator
will additionally enforce rules that span multiple files:

1. `dataset_id` is identical in all three documents.
2. `generated_at` in both source files equals `created_at` in the manifest.
3. The manifest generator seed equals the seed in `runs.json`.
4. Every run references a declared test case and GPU.
5. `run_id` and `testcase_id` values are unique in their respective collections.
6. Every manifest artifact has the declared byte length and SHA-256 digest.
7. Both `runs.json` and `capabilities.json` are present exactly once.
8. The manifest `snapshot_hash` matches the algorithm in ADR-005.

Schema validation is necessary but not sufficient: a structurally valid dataset
can still violate these semantic invariants.


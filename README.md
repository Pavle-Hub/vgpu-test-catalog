# vGPU Test Catalog

An academic demonstration of reliable AI-agent automation for maintaining a
software artifact. An agent reads synthetic measurements through MCP servers
and proposes updates to a test catalog. A deterministic checker independently
recomputes derived values and acts as a required CI gate.

## Core pattern

```text
pinned dataset -> MCP sources -> agent skill -> catalog proposal
                                            -> deterministic checker -> CI gate
```

The agent may write only contract-defined derived fields. Human-authored fields,
the source snapshot, derivation rules, and the merge decision remain outside the
agent's control.

## Planned components

- deterministic synthetic measurement generator;
- content-addressed dataset manifest;
- `metrics-mcp` tools for duration and pass-rate statistics;
- `env-mcp` resources for the GPU capability matrix;
- `rules.yaml` as the shared declarative contract;
- Markdown test catalog with field-level provenance;
- `sync-catalog` Cursor Skill with a bounded repair loop;
- `catalog-check` deterministic CLI;
- fault-injection evaluation framework;
- GitHub Actions required status check.

## Project status

The repository contains a versioned reference dataset, its deterministic
generator, JSON Schemas, a validated `rules.yaml` contract, and a mixed-ownership
Markdown catalog. `catalog-check` independently re-derives every exact field,
validates visible values and hidden provenance, and emits a structured JSON
report. Its local `--write` mode replaces only marker-bounded derived blocks.

## Development prerequisites

- Python 3.11-3.14 (Python 3.13 is recommended for the reference environment)
- Git
- Cursor for the agent demonstration

## Quick verification

From an activated development environment:

```powershell
python -m vgpu_catalog.validation dataset
python -m vgpu_catalog.derivation dataset --rules rules.yaml
python -m catalog_check.cli --check
python -m pytest
ruff check .
```

To demonstrate mechanical repair locally:

```powershell
python -m catalog_check.cli --write
```

Write mode is deliberately excluded from CI: a verifier must judge the proposed
artifact, not silently replace it.

The committed reference snapshot can be regenerated with:

```powershell
python -m vgpu_catalog.dataset --output dataset
```

## Documentation

- [Project scope](docs/project-scope.md)
- [Architecture decisions](docs/architecture-decisions.md)


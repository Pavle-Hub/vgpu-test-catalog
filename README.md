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
generator, JSON Schemas, and a cross-file provenance validator. The derivation
rules and deterministic catalog checker are the next implementation milestone.

## Development prerequisites

- Python 3.11-3.14 (Python 3.13 is recommended for the reference environment)
- Git
- Cursor for the agent demonstration

## Quick verification

From an activated development environment:

```powershell
python -m vgpu_catalog.validation dataset
python -m pytest
ruff check .
```

The committed reference snapshot can be regenerated with:

```powershell
python -m vgpu_catalog.dataset --output dataset
```

## Documentation

- [Project scope](docs/project-scope.md)
- [Architecture decisions](docs/architecture-decisions.md)


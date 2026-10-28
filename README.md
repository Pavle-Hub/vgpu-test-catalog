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

The repository contains a versioned reference dataset, a validated `rules.yaml`
contract, a mixed-ownership Markdown catalog, two read-only MCP 2.x servers, a
project-level Cursor and Codex integrations, a controlled evaluation framework,
and a GitHub Actions workflow awaiting hosted verification.
`metrics-mcp` exposes structured measurement tools; `env-mcp` exposes capability
resources. The `sync-catalog` Skill composes their evidence under a bounded
three-attempt repair policy. `catalog-check` independently reads the raw pinned
files rather than trusting either MCP response or the proposed artifact. Five
fault operators and clean controls measure checker and agent behavior separately.

## Development prerequisites

- Python 3.11-3.14 (Python 3.13 is recommended for the reference environment)
- Git
- Cursor or Codex for the agent demonstration

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
- [MCP server contracts and verification](docs/mcp-servers.md)
- [Cursor MCP and Skill workflow](docs/cursor-workflow.md)
- [Evaluation workflow](eval/README.md)
- [Isolated Codex experiments](docs/codex-experiments.md)
- [CI gate and merge protection](docs/ci-gate.md)
- [Completion checklist](docs/completion-checklist.md)


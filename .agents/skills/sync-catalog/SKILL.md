---
name: sync-catalog
description: Synchronize catalog/test_catalog.md from the project's pinned env-mcp and metrics-mcp evidence, preserve human-owned content, and validate with the bounded deterministic checker loop. Use for vGPU catalog synchronization or repair in this repository.
---

# Sync the vGPU catalog

Read `.cursor/skills/sync-catalog/SKILL.md` completely before acting. That file
is the canonical cross-client workflow and safety contract; follow every step
and stopping condition in it.

## Experiment mode

The default mode is `with-checker`. When the user explicitly supplies
`mode=without-checker`, perform the same evidence collection, derivation, and
protected-field checks, with these changes: skip canonical section 4 entirely,
make one proposal only, and do not run or read any deterministic checker,
derivation, writer, or test-suite output. In section 5 inspect protected text
and Git scope without requiring a checker report. Report zero checker attempts
and state that evaluator-side verification is pending. Do not run the checker
after that report. This mode measures one proposal without checker feedback.

Apply these Codex host requirements:

- Work from the repository root and use the project virtual environment.
- Require both project MCP servers configured in `.codex/config.toml`:
  `env-mcp` for compatibility resources and `metrics-mcp` for measurement
  tools. If either server is unavailable, stop and report that Codex must be
  restarted in this trusted project; do not replace MCP evidence with direct
  dataset inference.
- Use shell commands only for the source validator, the read-only checker, Git
  inspection, and other steps explicitly allowed by the canonical workflow.
- Edit only `catalog/test_catalog.md`. Do not modify experiment manifests or
  lifecycle state while synchronizing the catalog.
- Do not commit or push. Return control to the user after reporting the source
  hash, checker-attempt count, updated test cases and fields, Summary changes,
  protected-field result, and Git scope.

An explicit invocation is `$sync-catalog`.

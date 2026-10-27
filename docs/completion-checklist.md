# Completion checklist

Status checked on 2026-10-27.

## Implemented and locally verified

- Reference dataset, generator, manifest hashes, JSON schemas, and validation.
- Declarative rules and mixed-ownership Markdown catalog.
- Read-only metrics and environment MCP servers.
- Cursor Skill and Codex repository Skill with local MCP configuration.
- Independent deterministic checker and bounded agent repair workflow.
- Five deterministic fault operators and clean controls.
- Agent run recording, restoration, interruption, and protocol-filtered metrics.
- Historical frozen Cursor protocols and schedules.
- GitHub Actions workflow and merge-protection demonstration instructions.

Local verification: 83 tests pass. The checker detection suite contains 60
cases: 50 faults detected, 10 clean controls accepted, zero false positives and
zero false negatives on this controlled dataset. These numbers do not measure
agent repair success.

## Remaining implementation and evidence

1. Verify Skill discovery and both MCP servers in a fresh Codex project chat.
   Registration has been checked, but a complete Codex catalog sync has not yet
   been observed.
2. Agree and freeze the executable agent experiment configuration. The current
   v3 protocol names Cursor Grok 4.6 Medium and requires HEAD at `experiment-v3`.
   Current development has advanced beyond that tag, and Cursor quota is
   exhausted. Codex runs require their own accurately recorded agent protocol,
   prompts, and baseline; changing the client alone does not update v3.
3. Run the final paired agent experiments across all five fault classes and
   clean controls, including both checker modes and the chosen repetitions.
   No completed run is currently eligible under v3; its first run was interrupted.
4. Produce protocol-filtered final results, paired comparisons, and uncertainty
   estimates appropriate for the number of repetitions. Keep clean-control
   outcomes separate from fault repair rates in the thesis.
5. Push and verify the first hosted `Catalog CI` run. Validate installation of
   the locked packages on the clean GitHub runner.
6. Enable required `catalog-gate` checks on `main` and demonstrate an invalid PR
   whose merge is blocked. Capture hosted evidence as described in `ci-gate.md`.
7. Select representative input/output catalogs, JSON reports, tables, screenshots,
   and architecture figures for the thesis. Package the raw final results and
   transcripts for reproducibility; `eval/results/` is currently Git-ignored.
8. Freeze the final release and write the implementation, methodology, results,
   limitations, and conclusion chapters using the verified evidence.

The checker verifies the defined derived-data contract. Semantic Summary quality,
actual model selection in the client UI, and hosted branch-rule enforcement
need their own evidence and must not be inferred from a valid checker report.

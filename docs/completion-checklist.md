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
- Isolated Codex batch runner, candidate protocol, event auditing, and paired
  analysis/report generation. Live pilot verification is pending.

Local verification: 93 tests pass. The checker detection suite contains 60
cases: 50 faults detected, 10 clean controls accepted, zero false positives and
zero false negatives on this controlled dataset. These numbers do not measure
agent repair success.

## Remaining implementation and evidence

1. Verify Skill discovery and both MCP servers in a fresh Codex project chat.
   Registration has been checked, but a complete Codex catalog sync has not yet
   been observed. The batch pilot is the next integration check; launching a
   nested CLI from the desktop agent shell currently fails with Access denied.
2. Agree and freeze the executable agent experiment configuration. The current
   v3 protocol names Cursor Grok 4.6 Medium and requires HEAD at `experiment-v3`.
   Current development has advanced beyond that tag, and Cursor quota is
   exhausted. Codex runs require their own accurately recorded agent protocol,
   prompts, and baseline; changing the client alone does not update v3.
   `eval/codex-protocol.yaml` now provides the candidate; see
   `docs/codex-experiments.md` for the pilot and result-side freeze process.
3. Run the final paired agent experiments across all five fault classes and
   clean controls, including both checker modes and the chosen repetitions.
   No completed run is currently eligible under v3; its first run was interrupted.
4. Produce protocol-filtered final results, paired comparisons, and uncertainty
   estimates appropriate for the number of repetitions. Keep clean-control
   outcomes separate from fault repair rates in the thesis.
5. Hosted CI verification is complete for the current base implementation;
   rerun it for the Codex batch implementation when its PR is pushed.
6. The active `Protect main` ruleset requires `catalog-gate`; PR #1 demonstrates
   an incorrect timeout rejected at the checker step. The user captured a
   screenshot of the blocked merge. Retain that screenshot with the PR and run
   URLs as the final merge-enforcement evidence.
7. Select representative input/output catalogs, JSON reports, tables, screenshots,
   and architecture figures for the thesis. Package the raw final results and
   transcripts for reproducibility; `eval/results/` is currently Git-ignored.
8. Freeze the final release and write the implementation, methodology, results,
   limitations, and conclusion chapters using the verified evidence.

The checker verifies the defined derived-data contract. Semantic Summary quality,
actual model selection in the client UI, and hosted branch-rule enforcement
need their own evidence and must not be inferred from a valid checker report.

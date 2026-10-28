# Completion checklist

Status checked on 2026-10-28.

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
- Isolated Codex batch runner, verified two-mode pilot, frozen collection, and
  all 60 completed final sessions (plus one preserved, unscored interruption).
- Non-destructive offline command-audit correction, separate revised scores,
  paired comparisons, and uncertainty estimates. See
  `docs/codex-evaluation-results.md` for measured outcomes and limitations.

The checker detection suite contains 60
cases: 50 faults detected, 10 clean controls accepted, zero false positives and
zero false negatives on this controlled dataset. These numbers do not measure
agent repair success.

## Remaining implementation and evidence

1. Final Codex collection and corrected analysis are complete under
   `codex-agent-eval-1`, not historical Cursor v3. Preserve the original frozen
   protocol and raw scores alongside the documented audit-v2 correction.
   Do not relabel Codex results as Cursor results or rerun failed cases.
2. Hosted CI verification is complete for the current base implementation;
   rerun it for the Codex batch implementation when its PR is pushed.
3. The active `Protect main` ruleset requires `catalog-gate`; PR #1 demonstrates
   an incorrect timeout rejected at the checker step. The user captured a
   screenshot of the blocked merge. Retain that screenshot with the PR and run
   URLs as the final merge-enforcement evidence.
4. Three representative cases and a portable, hashed evidence pack are prepared;
   see `docs/representative-examples.md`. Capture the suggested evidence views
   and prepare aggregate charts and architecture figures for the thesis.
   The user reports a separate backup of the raw collection; `eval/results/`
   remains Git-ignored. Keep that archive alongside the portable examples.
5. Freeze the final release and write the implementation, methodology, results,
   limitations, and conclusion chapters using the verified evidence.

The checker verifies the defined derived-data contract. Semantic Summary quality,
actual model selection in the client UI, and hosted branch-rule enforcement
need their own evidence and must not be inferred from a valid checker report.

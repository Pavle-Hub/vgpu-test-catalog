# Evaluation framework

The evaluation layer separates two questions:

1. Does the deterministic checker detect catalog faults without rejecting clean
   controls?
2. Can a named agent configuration repair a fault while preserving protected
   human fields, with or without checker feedback?

Generated artifacts live under `eval/results/` and are ignored by Git. Publish
only deliberately selected, anonymized experiment results later.

## Fault classes

| Class | Controlled mutation | Expected checker signal |
| --- | --- | --- |
| `wrong-value` | Changes visible and hidden timeout consistently | exact field mismatch |
| `stale-value` | Replaces latest measurement with an old timestamp | exact field mismatch |
| `hallucinated-field` | Adds an undeclared readable and JSON field | schema error |
| `broken-format` | Removes a delimiter from hidden JSON | parse error |
| `false-provenance` | Keeps the value but changes its source hash | provenance mismatch |

Every operator is deterministic and changes exactly one selected derived block.

## Checker detection suite

Generate all five faults and one clean control for every catalog test case:

```powershell
.venv\Scripts\python.exe eval\inject_faults.py suite `
  --output eval\results\checker-suite-v1
```

For a fast one-test-case smoke run, add `--testcase TC-001`. `suite.json`
contains the full case manifest and confusion-matrix metrics:

- precision and recall/detection rate;
- false-pass rate (faulty catalogs accepted);
- false-fail rate (clean controls rejected);
- accuracy and raw TP/FN/FP/TN counts.

Each case directory also contains the exact catalog input and checker JSON
report, so every metric is auditable.

## Interactive Cursor agent run

Always begin from a clean worktree and a catalog for which
`catalog-check --check` passes. Start exactly one run:

```powershell
.venv\Scripts\python.exe eval\inject_faults.py start `
  --fault-class false-provenance `
  --testcase TC-001 `
  --model "Cursor Grok 4.6" `
  --mode with-checker `
  --run-id grok46-provenance-01
```

`start` first saves the valid baseline and faulty input under
`eval/results/runs/<run-id>/`, proves that the checker rejects the injection,
and only then replaces `catalog/test_catalog.md`. It refuses to start from an
invalid catalog or while another run is awaiting the agent or its restore step.

The run directory contains the exact prompt in `prompt.md`, and its SHA-256 is
stored in `run.json`. For `with-checker`, paste that prompt into Cursor; it
invokes `/sync-catalog`. For `without-checker`, the paired prompt requests one
MCP-based proposal while explicitly withholding deterministic checker feedback.
Do not paraphrase either prompt during measured runs.

Record the exact number of checker attempts reported by the Skill (`0` for the
without-checker prompt), then finish the run:

```powershell
.venv\Scripts\python.exe eval\inject_faults.py finish `
  --run-id grok46-provenance-01 `
  --checker-attempts 2
```

`finish` saves the agent output, runs an evaluator-side final check, and records
whether all `Purpose` and `Notes` values stayed byte-for-byte unchanged. It does
not overwrite the result, so the diff remains available for inspection.

After inspection, restore the recorded baseline:

```powershell
.venv\Scripts\python.exe eval\inject_faults.py restore `
  --run-id grok46-provenance-01
```

Restore refuses to overwrite edits made after `finish`. It also refuses an
unfinished run, ensuring that agent output is recorded before cleanup.

## Agent metrics

Aggregate all finished runs:

```powershell
.venv\Scripts\python.exe eval\inject_faults.py summarize `
  --output eval\results\agent-summary.json
```

The summary reports repair success, final checker validity, protected-field
compliance, escalation rate, and average checker attempts overall and grouped by
fault class, mode, and model. Use matched `with-checker` and `without-checker`
runs when comparing the effect of deterministic feedback.


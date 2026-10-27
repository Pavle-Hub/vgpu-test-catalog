# Isolated Codex experiments

The Codex experiment candidate is `eval/codex-protocol.yaml`. It is separate
from the historical Cursor protocols. It selects the locally configured Codex
model, `gpt-6.1-sol`, with high reasoning, CLI 0.163.0-alpha.11, and the existing
ChatGPT login. Actual account availability and end-to-end tool event recording
must be established by the pilot before final collection.

## Current verification boundary

Local deterministic tests verify plan generation, input isolation, transcript
auditing, interruption handling, and statistical reporting. They do not count
as live agent results. A minimal child CLI invocation from the desktop agent's
restricted shell currently fails before inference with:

```text
failed to initialize in-process app-server client: Access is denied. (os error 5)
```

Therefore the pilot must first be launched from the user's ordinary local
terminal. No live Codex repair or final agent statistic is claimed yet. The
runner does not disable the sandbox to work around this limitation.

## Run the pilot

Commit the implementation before measuring. From the project root in an
ordinary PowerShell terminal, run:

```powershell
.venv\Scripts\python.exe tools\run_codex_experiments.py --pilot
```

The runner searches PATH and the standard Codex desktop installation folders,
including `%USERPROFILE%/AppData/Local/OpenAI/Codex/bin/*/codex.exe`. It checks
the executable version against the candidate protocol. If discovery is still
unsuccessful, supply an explicit executable path with `--codex` for both pilot
and collection. No permanent PATH change or CLI reinstallation is required.

Because user configuration is excluded from measured sessions, the runner
explicitly sets workspace-write, on-request approvals, and invocation-scoped
trust for each generated workspace. On Windows it also selects the elevated
sandbox backend used by the desktop installation. These settings apply only to
the child invocation; no global trust entry or full-access mode is added.
Host-side policy rejections in stderr are recorded as infrastructure
interruptions even if the CLI returns zero and emits `turn.completed`.

On Windows, a per-user Python installation under AppData can be inaccessible to
the sandbox account. The runner copies the existing interpreter, standard
library, DLLs, and installed virtual-environment packages to
`eval/results/codex-eval-1/python-runtime/`. No download, package upgrade, or
global permission change is performed. A version/package identity marker
prevents silent reuse after the environment changes. The evaluator still runs
in the original environment.

Before a model call, a direct `codex sandbox <python> ...` preflight tests imports
and a temporary write under the generated workspace's catalog directory.
The pinned Windows CLI takes the executable directly after `sandbox`; it does
not accept a `windows` platform subcommand there.
Its stdout/stderr are preserved as `sandbox-preflight.*.txt`. If this fails, the
runner stops without invoking the model. The workspace includes a generated
`.codex/config.toml` matching its explicit MCP launch settings. The three local
metrics tools declare read-only, idempotent, closed-world annotations and are
explicitly approved for that child invocation only.

This runs an isolated hallucinated-field pair, one attempt per mode. The two
sessions use the same Skill, instructions, model, and source snapshot. The
explicit mode controls whether checker feedback is available. The source
validator remains allowed in both modes.

The runner requires an observable completed agent turn, env-mcp resource
evidence, metrics-mcp duration and pass-rate evidence, and a compliant checker
attempt count. It saves stdout JSONL events, stderr, the exact prompt and CLI
arguments, before/after catalogs, independent checker reports, and a command
audit. If the pilot is interrupted or the host's tool event format differs from
the parser's expectations, inspect the preserved logs and resolve that issue
before collecting final data. Do not manually mark the pilot as passed.

## Freeze and collect

After the pilot reports `Pilot integration verified`, run:

```powershell
.venv\Scripts\python.exe tools\run_codex_experiments.py --run-all
```

The runner requires exactly the same repository HEAD, all tracked file hashes,
candidate configuration, runtime versions, and plan as in the successful pilot.
It writes an immutable-by-policy `frozen-protocol.json` before the first final
run and refuses to mix a changed configuration with existing results. This
result-side frozen record, rather than a self-referential commit hash inside a
tracked protocol file, identifies the measured state.

The final plan contains 25 fault pairs and five clean pairs: 60 sessions. Pair
order is deterministically shuffled with seed 2026; the first mode alternates
between consecutive pairs. Each session gets a fresh exported workspace and
an ephemeral agent context. No previous transcripts or reports are copied.
The only Git commit inside each workspace contains the injected input, so Git
history cannot reveal the correct reference catalog. The main catalog is never
modified by the batch. This is context isolation, not a hardened filesystem
container; the agent is instructed to stay within its workspace.

Final evaluator checks use the original project sources and rules, not editable
copies in the agent workspace. File hashes detect changes outside the catalog.
The audit is a transparent command-text check, not a security proof against a
deliberately obfuscated agent. It detects direct dataset reads, deterministic
writers, test-suite/oracle use, history recovery, and wrong checker usage.

An infrastructure interruption stops the batch. Running `--run-all` again
explicitly resumes it: completed cases are skipped, and an interrupted case
gets a fresh attempt directory. Old artifacts are retained and interruptions
are unscored. Each run has a 15-minute timeout; on Windows the runner terminates
its own child process tree before evaluating the preserved output. A completed
but incorrect proposal is recorded as a failure and is not retried for a better
outcome.

## Analyze and retain evidence

The batch updates its reports after each completed attempt. To rebuild them:

```powershell
.venv\Scripts\python.exe tools\run_codex_experiments.py --summarize
```

Results are under `eval/results/codex-eval-1/`:

- `frozen-protocol.json` and `plan.json`: exact measured configuration;
- `pilots/`: excluded integration pilots;
- `runs/<run-id>/attempt-NN/`: complete inputs, outputs, logs, audits, and scores;
- `summary.json`: aggregate and per-class rates, Wilson intervals, matched
  outcomes, and exploratory exact paired tests;
- `results.csv`: one row per completed final run;
- `report.md`: table of fault repairs and clean-control preservation, reported
  separately with incomplete collection clearly marked.

With only five repetitions per class, uncertainty is substantial. Report the
raw paired counts and intervals, and avoid general claims about model quality.
The actual model seed is unavailable. Results belong to this dataset and the
recorded client/model configuration. Neither a passing test suite nor pilot
success is evidence that the final 60 sessions have been collected.

`eval/results/` is Git-ignored. Preserve the final directory separately and
select anonymized reports and transcripts for the thesis appendix. Do not
publish authentication files or unrelated user configuration.

The execution mechanism follows the official [Codex non-interactive mode
documentation](https://developers.openai.com/codex/noninteractive): fresh
`codex exec --ephemeral` invocations, JSONL events, saved final messages, and
existing local authentication.

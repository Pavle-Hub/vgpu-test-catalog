---
name: sync-catalog
description: Synchronize the vGPU Markdown catalog from the pinned MCP evidence and rules.yaml, then run a bounded deterministic repair loop. Use when the dataset, rules, or derived catalog fields have changed.
---

# Sync catalog

Update `catalog/test_catalog.md` from the two project MCP servers while preserving
the boundary between human-authored, semantic, and exactly derived content.

## Non-negotiable guardrails

- Treat `dataset/**`, `rules.yaml`, `schemas/**`, tests, and source code as
  read-only inputs. Never change them during this workflow.
- Edit only `catalog/test_catalog.md`.
- Preserve every `Purpose` and `Notes` value byte-for-byte.
- You may update `Summary`, but keep it between the configured minimum and
  maximum lengths and do not present it as deterministically verified prose.
- Place exact derived content only inside the matching
  `<!-- catalog:derived:start TC-NNN -->` and
  `<!-- catalog:derived:end TC-NNN -->` markers. Do not add, remove, duplicate,
  rename, or move test-case sections or markers. Outside those blocks, only the
  corresponding `Summary` may be updated.
- Never run `catalog-check --write` or `derive-catalog-data`. The agent proposal
  must come from MCP evidence; `catalog-check --check` is only the independent
  oracle and feedback channel.
- Do not commit, push, open a pull request, or change branch.
- Make at most three checker attempts in total: the initial check after the
  proposal plus at most two focused repair checks. Never reset this counter.

If a protected file is accidentally changed, stop and report the path. Do not
discard pre-existing user changes and do not attempt a broad rollback.

## 1. Establish the contract and protected text

1. Read `rules.yaml`, `dataset/manifest.json`,
   `schemas/catalog-derived.schema.json`, and `catalog/test_catalog.md`.
2. Record the current `Purpose` and `Notes` text for every `TC-NNN` section so it
   can be compared exactly after editing.
3. Run the source validator without modifying the snapshot:

   ```powershell
   .venv\Scripts\python.exe -m vgpu_catalog.validation dataset
   ```

   Stop without editing if validation fails.
4. From the manifest, record `dataset_id`, `snapshot_hash`, and `created_at`.
   The manifest `created_at` is the deterministic computation time and the end
   of the measurement window; never use the wall clock.

## 2. Collect evidence through both MCP servers

1. Read the `vgpu-env://capability-matrix` resource.
2. Call `list_testcases` from `metrics-mcp`.
3. Confirm that both responses have the manifest's `dataset_id`,
   `snapshot_hash`, and `created_at`/`snapshot_at`. Stop on any mismatch.
4. Use test cases from the capability matrix as the complete test-case set.
5. For each test case, read
   `vgpu-env://testcases/{testcase_id}/supported-gpus`. Confirm its identity
   fields match the same manifest.
6. For each supported test/GPU pair, call both `get_duration_stats` and
   `get_pass_rate` with `window_days` equal to
   `measurement_window.lookback_days` from `rules.yaml`.
7. Confirm identity fields, requested identifiers, window, counts, and
   timestamps in every response. For pass-rate evidence require
   `passed + failed == samples`. Stop if any response is missing, inconsistent,
   malformed, or has a different source hash.

Do not infer support from the presence of measurements. `env-mcp` is the sole
source of compatibility; `metrics-mcp` is the source of measurement evidence.

## 3. Derive the proposal

For each test case, apply only the current values in `rules.yaml`:

1. `supported_gpus.value` is the sorted list returned by the supported-GPU
   resource. Its status is `ok`.
2. Evidence is sufficient only if every supported GPU has at least
   `minimum_samples_per_gpu` samples in the requested window.
3. With sufficient evidence, timeout is
   `ceil(max(per-GPU p95_seconds) * timeout_margin)`. Otherwise its value is
   `null` and status is `insufficient-data`.
4. With sufficient evidence, calculate every per-GPU pass rate from exact
   integer counts as `passed / samples * 100`, choose the minimum, round that
   display value half-up to `decimal_places`, and assign the badge using the
   configured thresholds. Apply thresholds to the exact unrounded rate.
   Otherwise use a `null` percentage, value `insufficient-data`, and status
   `insufficient-data`.
5. `last_measurement.value` is the maximum non-null last-measurement timestamp
   for the test case. It is `fresh` when it is on or after
   `created_at - maximum_age_days`; otherwise it is `stale`.
6. Every provenance object uses the manifest `snapshot_hash` as `source_hash`
   and manifest `created_at` as `computed_at`.

Use these exact formula strings in hidden JSON, substituting current rule
values where shown:

- Supported GPUs: `required_capabilities subset_of gpu.capabilities`
- Timeout: `requires_each_gpu_samples>={minimum}; ceil(max_gpu(nearest_rank_p{percentile}(duration_seconds)) * {margin})`
- Pass rate: `requires_each_gpu_samples>={minimum}; min_gpu(passed / samples * 100), round_half_up({decimal_places}); healthy>={healthy}, degraded>={degraded}`
- Freshness: `max(executed_at); fresh_if_age_days<={maximum_age_days}`

Update both the readable Markdown lines and the hidden JSON in each derived
block. Follow the existing block's indentation, key order, number formatting,
and `format_version`. The two representations must describe identical values.
Keep each Summary concise and supported by the gathered evidence.

## 4. Verify and repair with a hard limit

Set an attempt counter to zero. Then perform this loop:

1. Increment the counter.
2. Run exactly this read-only command:

   ```powershell
   .venv\Scripts\python.exe -m catalog_check.cli --check
   ```

3. Parse the JSON report from standard output.
4. If `valid` is `true`, leave the loop immediately.
5. If `valid` is `false` and the counter is below three, edit only the paths
   named in `issues`. Use each issue's `expected` and `actual` values as focused
   feedback; do not regenerate unrelated prose or blocks. Then repeat.
6. If the third report is invalid, stop. Report the remaining issue codes,
   paths, and messages to the user. Do not guess, broaden edits, run write mode,
   or make a fourth attempt.

Structural errors, missing markers, source-hash disagreement, unavailable MCP
servers, invalid source data, and protected-field drift require human review.
Do not try to repair those by changing source inputs or human-owned content.

## 5. Final safety checks

After a valid checker report:

1. Compare all recorded `Purpose` and `Notes` values with the current file and
   require byte-for-byte equality.
2. Run `git diff -- catalog/test_catalog.md` and inspect the complete diff.
3. Run `git status --short` and verify this workflow changed no other file.
4. Report the source hash, checker attempts used, test cases updated, and any
   Summary changes. Leave commit and push decisions to the user.

# Architecture decisions

This file records decisions that affect reproducibility or the validity of the
evaluation. Each decision should be updated before implementation depends on it.

## ADR-001: Public synthetic repository

- **Status:** accepted
- **Decision:** all measurements, GPU identifiers, and test cases are synthetic.
- **Reason:** the full experiment must be public, reproducible, and independent
  of proprietary systems.

## ADR-002: Deterministic verifier precedes the agent

- **Status:** accepted
- **Decision:** implement and test the derivation oracle before implementing the
  MCP servers and the agent skill.
- **Reason:** an agent cannot be evaluated until correct output is independently
  defined.

## ADR-003: Pinned source snapshot

- **Status:** accepted
- **Decision:** CI verifies a repository-pinned snapshot and its content hash.
- **Reason:** a live data source cannot provide a reproducible CI decision unless
  the checked version is fixed.

## ADR-004: Checker independence

- **Status:** accepted
- **Decision:** the agent and checker read the same declarative contract, but the
  checker reads raw pinned data and independently computes expected values. CI
  never invokes a write/fix mode.
- **Reason:** the verifier must not trust the proposal it verifies.

## ADR-005: Snapshot identity

- **Status:** accepted
- **Decision:** each source artifact is hashed as its exact UTF-8 file bytes with
  SHA-256. `snapshot_hash` is the SHA-256 digest of a UTF-8 canonical JSON array
  containing each artifact's `path`, `bytes`, and `sha256`, sorted by `path`.
  Canonical JSON uses sorted object keys, no insignificant whitespace, and no
  ASCII escaping (`sort_keys=True`, `separators=(",", ":")`,
  `ensure_ascii=False`). The manifest itself is not part of this hash.
- **Reason:** excluding the manifest avoids a self-referential hash, while file
  hashes preserve sensitivity to every byte of both authoritative sources.

## ADR-006: Supported GPU derivation

- **Status:** accepted
- **Decision:** a GPU supports a test case exactly when the test case's required
  capability set is a subset of the GPU's capability set. The source stores
  capabilities and requirements, not a second precomputed support list.
- **Reason:** one directional rule avoids duplicated data that could disagree.

## ADR-007: Reproducible synthetic distribution

- **Status:** accepted
- **Decision:** the reference snapshot uses Python 3.13, seed `2026`, a fixed
  logical generation timestamp, integer arithmetic for duration variation, and
  deterministic run ordering. Supported pairs receive 30 samples except
  `TC-010` on `GPU-C`, which receives five.
- **Reason:** fixed inputs make byte-for-byte regeneration testable. The sparse
  pair provides a controlled `insufficient-data` case for later evaluation.

## ADR-008: Statistical derivation contract

- **Status:** accepted
- **Decision:** metrics use a 30-day inclusive lookback window. A test case is
  `insufficient-data` for timeout and pass rate when any supported GPU has fewer
  than 10 samples in that window. The configured percentile uses nearest-rank;
  timeout is `ceil(maximum GPU p95 × 1.25)`. Pass rate is the minimum per-GPU
  rate and is rounded half-up to two decimal places. Measurements older than 30
  days at the pinned snapshot time are stale.
- **Reason:** the definitions are conservative, transparent, and independent of
  statistics-library interpolation defaults. Requiring evidence for every
  supported GPU prevents a well-sampled platform from hiding an unsupported
  estimate on another platform.

## ADR-009: Deterministic derivation time

- **Status:** accepted
- **Decision:** derived-field `computed_at` is the pinned manifest `created_at`,
  never the wall-clock time at which a command happens to run. Every derived
  field also records the snapshot hash and its formula.
- **Reason:** identical repository inputs must produce identical expected state
  on a laptop and in CI.

## ADR-010: Mixed-ownership Markdown format

- **Status:** accepted
- **Decision:** every `## TC-NNN` section contains human-owned `Purpose` and
  `Notes`, one `Derived fields` block bounded by testcase-specific HTML comment
  markers, and a semantic `Summary`. The derived block contains both readable
  Markdown and versioned hidden JSON. The JSON stores each exact value, status,
  source hash, formula, and deterministic computation timestamp.
- **Reason:** Markdown stays useful to readers while explicit boundaries permit
  safe mechanical replacement. Checking both representations prevents an agent
  from changing the visible value while leaving correct hidden metadata.

## ADR-011: Checker and write-mode separation

- **Status:** accepted
- **Decision:** `catalog-check --check` is read-only, independently re-derives
  values from the pinned dataset, and reports structured differences. Local
  `--write` replaces only a complete, uniquely paired derived block and refuses
  malformed structure. CI will invoke only `--check`.
- **Reason:** automatic repair is useful in an agent feedback loop, but CI that
  repairs the proposal would no longer verify what the agent actually wrote.

## ADR-012: Semantic verification boundary

- **Status:** accepted
- **Decision:** the exact checker validates only the presence and configured
  length range of `Summary`; it does not claim that the prose is factually or
  stylistically correct.
- **Reason:** exact numerical and provenance claims have a deterministic oracle,
  while open-ended natural-language quality does not. The distinction is part
  of the experiment rather than hidden behind a false binary guarantee.

## Decisions still to define

- model identifier and Cursor settings used in agent experiments.


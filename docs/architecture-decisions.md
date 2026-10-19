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

## Decisions still to define

- percentile interpolation method;
- catalog machine-readable block format;
- model identifier and Cursor settings used in agent experiments.


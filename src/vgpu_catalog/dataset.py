"""Deterministic synthetic dataset generation."""

from __future__ import annotations

import argparse
import json
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from vgpu_catalog import __version__
from vgpu_catalog.hashing import artifact_record, compute_snapshot_hash, pretty_json_bytes
from vgpu_catalog.schema_validation import iter_schema_errors

DEFAULT_SEED = 2026
DEFAULT_DATASET_ID = "dataset-reference-2026"
DEFAULT_GENERATED_AT = "2026-01-01T00:00:00Z"
DEFAULT_RUNS_PER_PAIR = 30
DEFAULT_SPARSE_SAMPLES = 5
SPARSE_PAIR = ("TC-010", "GPU-C")

GPU_DEFINITIONS: tuple[dict[str, Any], ...] = (
    {
        "gpu_id": "GPU-A",
        "capabilities": ["compute-basic", "graphics"],
    },
    {
        "gpu_id": "GPU-B",
        "capabilities": [
            "compute-basic",
            "compute-advanced",
            "graphics",
            "large-memory",
        ],
    },
    {
        "gpu_id": "GPU-C",
        "capabilities": [
            "compute-basic",
            "compute-advanced",
            "graphics",
            "large-memory",
            "multi-instance",
        ],
    },
)

TESTCASE_DEFINITIONS: tuple[dict[str, Any], ...] = (
    {"testcase_id": "TC-001", "required_capabilities": ["compute-basic"]},
    {"testcase_id": "TC-002", "required_capabilities": ["graphics"]},
    {"testcase_id": "TC-003", "required_capabilities": ["compute-advanced"]},
    {"testcase_id": "TC-004", "required_capabilities": ["large-memory"]},
    {"testcase_id": "TC-005", "required_capabilities": ["multi-instance"]},
    {
        "testcase_id": "TC-006",
        "required_capabilities": ["compute-advanced", "graphics"],
    },
    {
        "testcase_id": "TC-007",
        "required_capabilities": ["compute-basic", "large-memory"],
    },
    {
        "testcase_id": "TC-008",
        "required_capabilities": ["compute-advanced", "multi-instance"],
    },
    {
        "testcase_id": "TC-009",
        "required_capabilities": ["graphics", "large-memory"],
    },
    {
        "testcase_id": "TC-010",
        "required_capabilities": [
            "compute-advanced",
            "large-memory",
            "multi-instance",
        ],
    },
)

GPU_DURATION_FACTORS = {"GPU-A": 115, "GPU-B": 85, "GPU-C": 130}
GPU_PASS_THRESHOLDS = {"GPU-A": 9400, "GPU-B": 9800, "GPU-C": 9000}


def _parse_utc_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo != UTC:
        raise ValueError("generated_at must use the UTC Z suffix")
    return parsed


def _format_utc_timestamp(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _supports(gpu: dict[str, Any], testcase: dict[str, Any]) -> bool:
    return set(testcase["required_capabilities"]).issubset(gpu["capabilities"])


def generate_documents(
    *,
    seed: int = DEFAULT_SEED,
    dataset_id: str = DEFAULT_DATASET_ID,
    generated_at: str = DEFAULT_GENERATED_AT,
    runs_per_pair: int = DEFAULT_RUNS_PER_PAIR,
    sparse_samples: int = DEFAULT_SPARSE_SAMPLES,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return deterministic run and capability documents."""

    if runs_per_pair < 1:
        raise ValueError("runs_per_pair must be at least 1")
    if not 1 <= sparse_samples <= runs_per_pair:
        raise ValueError("sparse_samples must be between 1 and runs_per_pair")

    timestamp = _parse_utc_timestamp(generated_at)
    rng = random.Random(seed)
    runs: list[dict[str, Any]] = []
    sequence = 1
    start_time = timestamp - timedelta(days=30)

    for testcase_index, testcase in enumerate(TESTCASE_DEFINITIONS, start=1):
        for gpu in GPU_DEFINITIONS:
            if not _supports(gpu, testcase):
                continue

            pair = (testcase["testcase_id"], gpu["gpu_id"])
            sample_count = sparse_samples if pair == SPARSE_PAIR else runs_per_pair

            for _ in range(sample_count):
                base_duration_ms = 10_000 + testcase_index * 4_000
                duration_factor = GPU_DURATION_FACTORS[gpu["gpu_id"]]
                jitter = rng.randint(8500, 11500)
                duration_ms = max(1, base_duration_ms * duration_factor * jitter // 1_000_000)

                pass_threshold = max(
                    7500,
                    GPU_PASS_THRESHOLDS[gpu["gpu_id"]] - testcase_index * 40,
                )
                status = "passed" if rng.randrange(10_000) < pass_threshold else "failed"
                executed_at = start_time + timedelta(hours=sequence)

                runs.append(
                    {
                        "run_id": f"run-{sequence:08d}",
                        "testcase_id": testcase["testcase_id"],
                        "gpu_id": gpu["gpu_id"],
                        "status": status,
                        "duration_seconds": round(duration_ms / 1000, 3),
                        "iterations": 50 + testcase_index * 10 + rng.randrange(21),
                        "executed_at": _format_utc_timestamp(executed_at),
                    }
                )
                sequence += 1

    capabilities = {
        "schema_version": "1.0",
        "dataset_id": dataset_id,
        "generated_at": generated_at,
        "gpus": list(GPU_DEFINITIONS),
        "testcases": list(TESTCASE_DEFINITIONS),
    }
    run_document = {
        "schema_version": "1.0",
        "dataset_id": dataset_id,
        "seed": seed,
        "generated_at": generated_at,
        "runs": runs,
    }

    errors = [
        *iter_schema_errors("runs", run_document),
        *iter_schema_errors("capabilities", capabilities),
    ]
    if errors:
        raise ValueError("Generated data violates its schema:\n" + "\n".join(errors))

    return run_document, capabilities


def write_dataset(
    output_dir: Path,
    *,
    seed: int = DEFAULT_SEED,
    dataset_id: str = DEFAULT_DATASET_ID,
    generated_at: str = DEFAULT_GENERATED_AT,
    runs_per_pair: int = DEFAULT_RUNS_PER_PAIR,
    sparse_samples: int = DEFAULT_SPARSE_SAMPLES,
) -> dict[str, Any]:
    """Generate and atomically replace the three dataset artifacts."""

    output_dir.mkdir(parents=True, exist_ok=True)
    runs, capabilities = generate_documents(
        seed=seed,
        dataset_id=dataset_id,
        generated_at=generated_at,
        runs_per_pair=runs_per_pair,
        sparse_samples=sparse_samples,
    )

    source_documents = {
        "runs.json": runs,
        "capabilities.json": capabilities,
    }
    for filename, document in source_documents.items():
        target = output_dir / filename
        temporary = output_dir / f".{filename}.tmp"
        temporary.write_bytes(pretty_json_bytes(document))
        temporary.replace(target)

    artifacts = [artifact_record(output_dir / name) for name in sorted(source_documents)]
    manifest = {
        "schema_version": "1.0",
        "dataset_id": dataset_id,
        "created_at": generated_at,
        "generator": {
            "name": "gen_dataset",
            "version": __version__,
            "seed": seed,
        },
        "artifacts": artifacts,
        "snapshot_hash": compute_snapshot_hash(artifacts),
    }

    manifest_errors = iter_schema_errors("manifest", manifest)
    if manifest_errors:
        raise ValueError("Generated manifest violates its schema:\n" + "\n".join(manifest_errors))

    manifest_path = output_dir / "manifest.json"
    temporary_manifest = output_dir / ".manifest.json.tmp"
    temporary_manifest.write_bytes(pretty_json_bytes(manifest))
    temporary_manifest.replace(manifest_path)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("dataset"))
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--dataset-id", default=DEFAULT_DATASET_ID)
    parser.add_argument("--generated-at", default=DEFAULT_GENERATED_AT)
    parser.add_argument("--runs-per-pair", type=int, default=DEFAULT_RUNS_PER_PAIR)
    parser.add_argument("--sparse-samples", type=int, default=DEFAULT_SPARSE_SAMPLES)
    args = parser.parse_args()

    manifest = write_dataset(
        args.output,
        seed=args.seed,
        dataset_id=args.dataset_id,
        generated_at=args.generated_at,
        runs_per_pair=args.runs_per_pair,
        sparse_samples=args.sparse_samples,
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

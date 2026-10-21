"""Deterministically derive expected catalog fields from a pinned dataset."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any

from vgpu_catalog.rules import DEFAULT_RULES_PATH, CatalogRules, load_rules
from vgpu_catalog.validation import validate_dataset


class DerivationError(ValueError):
    """Raised when expected catalog state cannot be derived safely."""


def nearest_rank_percentile(values: Iterable[Decimal], percentile: int) -> Decimal:
    """Return a percentile using the deterministic nearest-rank definition."""

    ordered = sorted(values)
    if not ordered:
        raise ValueError("Cannot calculate a percentile from an empty sequence.")
    if not 1 <= percentile <= 100:
        raise ValueError("percentile must be between 1 and 100.")

    rank = (percentile * len(ordered) + 99) // 100
    return ordered[rank - 1]


def _parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo != UTC:
        raise DerivationError(f"Timestamp must be expressed as UTC with Z: {value}")
    return parsed


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"), parse_float=Decimal)


def _supports(gpu: dict[str, Any], testcase: dict[str, Any]) -> bool:
    return set(testcase["required_capabilities"]).issubset(gpu["capabilities"])


def _decimal_number(value: Decimal, decimal_places: int) -> int | float:
    if decimal_places == 0:
        return int(value)
    return float(value)


def _provenance(source_hash: str, formula: str, computed_at: str) -> dict[str, str]:
    return {
        "source_hash": source_hash,
        "formula": formula,
        "computed_at": computed_at,
    }


def _gpu_statistics(
    records: list[dict[str, Any]],
    *,
    percentile: int,
) -> dict[str, Any]:
    durations = [Decimal(str(record["duration_seconds"])) for record in records]
    passed = sum(record["status"] == "passed" for record in records)
    samples = len(records)
    exact_pass_rate = Decimal(passed) * Decimal(100) / Decimal(samples)

    return {
        "samples": samples,
        "passed": passed,
        "duration_percentile_seconds": nearest_rank_percentile(durations, percentile),
        "max_duration_seconds": max(durations),
        "exact_pass_rate_percent": exact_pass_rate,
        "last_measurement": max(record["executed_at"] for record in records),
    }


def _derive_testcase(
    testcase: dict[str, Any],
    gpus: list[dict[str, Any]],
    runs_by_pair: dict[tuple[str, str], list[dict[str, Any]]],
    all_runs_by_testcase: dict[str, list[dict[str, Any]]],
    *,
    rules: CatalogRules,
    source_hash: str,
    computed_at: str,
) -> dict[str, Any]:
    testcase_id = testcase["testcase_id"]
    supported_gpus = sorted(gpu["gpu_id"] for gpu in gpus if _supports(gpu, testcase))
    minimum_samples = rules.measurement_window.minimum_samples_per_gpu

    stats_by_gpu: dict[str, dict[str, Any] | None] = {}
    for gpu_id in supported_gpus:
        records = runs_by_pair.get((testcase_id, gpu_id), [])
        stats_by_gpu[gpu_id] = (
            _gpu_statistics(records, percentile=rules.duration.percentile) if records else None
        )

    sufficient = bool(stats_by_gpu) and all(
        stats is not None and stats["samples"] >= minimum_samples for stats in stats_by_gpu.values()
    )
    timeout_value: int | None = None
    pass_rate_value: int | float | None = None
    pass_rate_badge = "insufficient-data"
    field_status = "ok" if sufficient else "insufficient-data"

    if sufficient:
        available_stats = [stats for stats in stats_by_gpu.values() if stats is not None]
        worst_duration = max(stats["duration_percentile_seconds"] for stats in available_stats)
        timeout_value = int(
            (worst_duration * rules.duration.timeout_margin).to_integral_value(
                rounding=ROUND_CEILING
            )
        )

        worst_pass_rate = min(stats["exact_pass_rate_percent"] for stats in available_stats)
        quantum = Decimal(1).scaleb(-rules.pass_rate.decimal_places)
        rounded_pass_rate = worst_pass_rate.quantize(quantum, rounding=ROUND_HALF_UP)
        pass_rate_value = _decimal_number(rounded_pass_rate, rules.pass_rate.decimal_places)
        if worst_pass_rate >= rules.pass_rate.healthy_minimum_percent:
            pass_rate_badge = "healthy"
        elif worst_pass_rate >= rules.pass_rate.degraded_minimum_percent:
            pass_rate_badge = "degraded"
        else:
            pass_rate_badge = "critical"

    all_testcase_runs = all_runs_by_testcase.get(testcase_id, [])
    last_measurement = (
        max(record["executed_at"] for record in all_testcase_runs) if all_testcase_runs else None
    )
    snapshot_time = _parse_timestamp(computed_at)
    freshness_cutoff = snapshot_time - timedelta(days=rules.freshness.maximum_age_days)
    is_fresh = (
        last_measurement is not None and _parse_timestamp(last_measurement) >= freshness_cutoff
    )

    percentile = rules.duration.percentile
    margin = format(rules.duration.timeout_margin, "f")
    decimal_places = rules.pass_rate.decimal_places
    healthy = format(rules.pass_rate.healthy_minimum_percent, "f")
    degraded = format(rules.pass_rate.degraded_minimum_percent, "f")
    freshness_days = rules.freshness.maximum_age_days
    gpu_evidence = {
        gpu_id: {
            "samples": stats["samples"] if stats else 0,
            "passed": stats["passed"] if stats else 0,
        }
        for gpu_id, stats in stats_by_gpu.items()
    }

    return {
        "testcase_id": testcase_id,
        "supported_gpus": {
            "value": supported_gpus,
            "status": "ok",
            "provenance": _provenance(
                source_hash,
                "required_capabilities subset_of gpu.capabilities",
                computed_at,
            ),
        },
        "timeout_seconds": {
            "value": timeout_value,
            "status": field_status,
            "evidence": gpu_evidence,
            "provenance": _provenance(
                source_hash,
                f"requires_each_gpu_samples>={minimum_samples}; "
                f"ceil(max_gpu(nearest_rank_p{percentile}(duration_seconds)) * {margin})",
                computed_at,
            ),
        },
        "pass_rate_badge": {
            "value": pass_rate_badge,
            "pass_rate_percent": pass_rate_value,
            "status": field_status,
            "evidence": gpu_evidence,
            "provenance": _provenance(
                source_hash,
                f"requires_each_gpu_samples>={minimum_samples}; "
                f"min_gpu(passed / samples * 100), round_half_up({decimal_places}); "
                f"healthy>={healthy}, degraded>={degraded}",
                computed_at,
            ),
        },
        "last_measurement": {
            "value": last_measurement,
            "status": "fresh" if is_fresh else "stale",
            "provenance": _provenance(
                source_hash,
                f"max(executed_at); fresh_if_age_days<={freshness_days}",
                computed_at,
            ),
        },
    }


def derive_catalog(
    dataset_dir: Path,
    rules_path: Path = DEFAULT_RULES_PATH,
) -> dict[str, Any]:
    """Return the complete deterministic state expected from the catalog."""

    dataset_dir = dataset_dir.resolve()
    report = validate_dataset(dataset_dir)
    if not report.valid:
        details = "; ".join(f"{issue.code}: {issue.path}" for issue in report.issues)
        raise DerivationError(f"Dataset validation failed: {details}")

    rules = load_rules(rules_path)
    runs_document = _load_json(dataset_dir / "runs.json")
    capabilities = _load_json(dataset_dir / "capabilities.json")
    manifest = _load_json(dataset_dir / "manifest.json")

    computed_at = manifest["created_at"]
    snapshot_time = _parse_timestamp(computed_at)
    window_start = snapshot_time - timedelta(days=rules.measurement_window.lookback_days)

    runs_by_pair: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    all_runs_by_testcase: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for run in runs_document["runs"]:
        all_runs_by_testcase[run["testcase_id"]].append(run)
        executed_at = _parse_timestamp(run["executed_at"])
        if window_start <= executed_at <= snapshot_time:
            runs_by_pair[(run["testcase_id"], run["gpu_id"])].append(run)

    testcases = [
        _derive_testcase(
            testcase,
            capabilities["gpus"],
            runs_by_pair,
            all_runs_by_testcase,
            rules=rules,
            source_hash=manifest["snapshot_hash"],
            computed_at=computed_at,
        )
        for testcase in sorted(capabilities["testcases"], key=lambda item: item["testcase_id"])
    ]

    return {
        "schema_version": "1.0",
        "dataset_id": manifest["dataset_id"],
        "source_hash": manifest["snapshot_hash"],
        "rules_version": rules.schema_version,
        "computed_at": computed_at,
        "testcases": testcases,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset_dir", nargs="?", type=Path, default=Path("dataset"))
    parser.add_argument("--rules", type=Path, default=DEFAULT_RULES_PATH)
    args = parser.parse_args()

    try:
        expected = derive_catalog(args.dataset_dir, args.rules)
    except (DerivationError, ValueError) as error:
        print(json.dumps({"valid": False, "error": str(error)}, ensure_ascii=False, indent=2))
        return 1

    print(json.dumps(expected, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

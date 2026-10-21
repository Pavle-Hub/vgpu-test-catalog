"""Deterministic measurement service behind the metrics MCP tools."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from metrics_mcp.models import (
    DurationStatsResult,
    PassRateResult,
    TestcaseListResult,
    TestcaseMeasurements,
)
from vgpu_catalog.derivation import nearest_rank_percentile
from vgpu_catalog.snapshot import DEFAULT_DATASET_DIR, DatasetSnapshot, load_snapshot


class MetricsQueryError(ValueError):
    """Raised for an invalid metrics query rather than an internal failure."""


def _parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo != UTC:
        raise MetricsQueryError(f"Timestamp must use UTC Z notation: {value}")
    return parsed


def _format_timestamp(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


class MetricsService:
    """Immutable in-memory view of one validated dataset snapshot."""

    def __init__(self, dataset_dir: Path = DEFAULT_DATASET_DIR) -> None:
        self.snapshot: DatasetSnapshot = load_snapshot(dataset_dir)
        capabilities = self.snapshot.capabilities
        self._testcase_ids = {testcase["testcase_id"] for testcase in capabilities["testcases"]}
        self._gpu_ids = {gpu["gpu_id"] for gpu in capabilities["gpus"]}
        self._runs_by_pair: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        for run in self.snapshot.runs["runs"]:
            self._runs_by_pair[(run["testcase_id"], run["gpu_id"])].append(run)

    def _validate_query(self, testcase_id: str, gpu_id: str, window_days: int) -> None:
        if testcase_id not in self._testcase_ids:
            raise MetricsQueryError(f"Unknown testcase_id: {testcase_id}")
        if gpu_id not in self._gpu_ids:
            raise MetricsQueryError(f"Unknown gpu_id: {gpu_id}")
        if not 1 <= window_days <= 3650:
            raise MetricsQueryError("window_days must be between 1 and 3650")

    def _window(
        self,
        testcase_id: str,
        gpu_id: str,
        window_days: int,
    ) -> tuple[list[dict[str, Any]], str, str]:
        self._validate_query(testcase_id, gpu_id, window_days)
        window_end = _parse_timestamp(self.snapshot.snapshot_at)
        window_start = window_end - timedelta(days=window_days)
        records = [
            run
            for run in self._runs_by_pair.get((testcase_id, gpu_id), [])
            if window_start <= _parse_timestamp(run["executed_at"]) <= window_end
        ]
        return records, _format_timestamp(window_start), _format_timestamp(window_end)

    def list_testcases(self) -> TestcaseListResult:
        measured_gpus: dict[str, set[str]] = defaultdict(set)
        for testcase_id, gpu_id in self._runs_by_pair:
            measured_gpus[testcase_id].add(gpu_id)

        return TestcaseListResult(
            dataset_id=self.snapshot.dataset_id,
            source_hash=self.snapshot.source_hash,
            snapshot_at=self.snapshot.snapshot_at,
            testcases=[
                TestcaseMeasurements(
                    testcase_id=testcase_id,
                    gpus_with_measurements=sorted(measured_gpus[testcase_id]),
                )
                for testcase_id in sorted(self._testcase_ids)
            ],
        )

    def get_duration_stats(
        self,
        testcase_id: str,
        gpu_id: str,
        window_days: int = 30,
    ) -> DurationStatsResult:
        records, window_start, window_end = self._window(testcase_id, gpu_id, window_days)
        durations = [Decimal(str(run["duration_seconds"])) for run in records]

        return DurationStatsResult(
            dataset_id=self.snapshot.dataset_id,
            source_hash=self.snapshot.source_hash,
            testcase_id=testcase_id,
            gpu_id=gpu_id,
            window_days=window_days,
            window_start=window_start,
            window_end=window_end,
            samples=len(records),
            passed=sum(run["status"] == "passed" for run in records),
            p50_seconds=float(nearest_rank_percentile(durations, 50)) if durations else None,
            p95_seconds=float(nearest_rank_percentile(durations, 95)) if durations else None,
            max_seconds=float(max(durations)) if durations else None,
            last_measurement=max((run["executed_at"] for run in records), default=None),
        )

    def get_pass_rate(
        self,
        testcase_id: str,
        gpu_id: str,
        window_days: int = 30,
    ) -> PassRateResult:
        records, window_start, window_end = self._window(testcase_id, gpu_id, window_days)
        samples = len(records)
        passed = sum(run["status"] == "passed" for run in records)
        pass_rate: float | None = None
        if samples:
            pass_rate = passed * 100 / samples

        return PassRateResult(
            dataset_id=self.snapshot.dataset_id,
            source_hash=self.snapshot.source_hash,
            testcase_id=testcase_id,
            gpu_id=gpu_id,
            window_days=window_days,
            window_start=window_start,
            window_end=window_end,
            samples=samples,
            passed=passed,
            failed=samples - passed,
            pass_rate_percent=pass_rate,
            last_measurement=max((run["executed_at"] for run in records), default=None),
        )

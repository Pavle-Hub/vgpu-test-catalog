from pathlib import Path

import pytest

from metrics_mcp.service import MetricsQueryError, MetricsService


@pytest.fixture(scope="module")
def metrics() -> MetricsService:
    return MetricsService(Path("dataset"))


def test_list_testcases_is_sorted_and_snapshot_pinned(metrics: MetricsService) -> None:
    result = metrics.list_testcases()

    assert result.dataset_id == "dataset-reference-2026"
    assert result.source_hash == (
        "83c9a22581b017a0ebc967d7c5bd4ef53f6c9edcb246e696ab402314a5eef394"
    )
    assert [item.testcase_id for item in result.testcases] == [
        f"TC-{index:03d}" for index in range(1, 11)
    ]


def test_duration_stats_use_explicit_nearest_rank(metrics: MetricsService) -> None:
    result = metrics.get_duration_stats("TC-001", "GPU-A")

    assert result.samples == 30
    assert result.passed == 27
    assert result.p50_seconds == 16.314
    assert result.p95_seconds == 18.395
    assert result.max_seconds == 18.415
    assert result.last_measurement == "2025-12-03T06:00:00Z"


def test_pass_rate_reports_sparse_raw_evidence(metrics: MetricsService) -> None:
    result = metrics.get_pass_rate("TC-010", "GPU-C")

    assert result.samples == 5
    assert result.passed == 4
    assert result.failed == 1
    assert result.pass_rate_percent == 80.0

    repeating = metrics.get_pass_rate("TC-003", "GPU-C")
    assert repeating.pass_rate_percent == pytest.approx(86.66666666666667)


def test_known_pair_without_measurements_returns_empty_statistics(
    metrics: MetricsService,
) -> None:
    result = metrics.get_duration_stats("TC-005", "GPU-A")

    assert result.samples == 0
    assert result.p50_seconds is None
    assert result.p95_seconds is None
    assert result.max_seconds is None
    assert result.last_measurement is None


@pytest.mark.parametrize(
    ("testcase_id", "gpu_id", "window_days", "message"),
    [
        ("TC-999", "GPU-A", 30, "Unknown testcase_id"),
        ("TC-001", "GPU-Z", 30, "Unknown gpu_id"),
        ("TC-001", "GPU-A", 0, "window_days"),
    ],
)
def test_invalid_metrics_query_is_explicit(
    metrics: MetricsService,
    testcase_id: str,
    gpu_id: str,
    window_days: int,
    message: str,
) -> None:
    with pytest.raises(MetricsQueryError, match=message):
        metrics.get_pass_rate(testcase_id, gpu_id, window_days)

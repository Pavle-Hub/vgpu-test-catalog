from decimal import Decimal
from pathlib import Path

import pytest

from vgpu_catalog.dataset import write_dataset
from vgpu_catalog.derivation import DerivationError, derive_catalog, nearest_rank_percentile


@pytest.mark.parametrize(
    ("percentile", "expected"),
    [
        (1, Decimal("1")),
        (50, Decimal("2")),
        (95, Decimal("4")),
        (100, Decimal("4")),
    ],
)
def test_nearest_rank_percentile_is_explicit(percentile: int, expected: Decimal) -> None:
    values = [Decimal("4"), Decimal("1"), Decimal("3"), Decimal("2")]

    assert nearest_rank_percentile(values, percentile) == expected


def test_nearest_rank_rejects_empty_input() -> None:
    with pytest.raises(ValueError, match="empty sequence"):
        nearest_rank_percentile([], 95)


def test_reference_derivation_has_expected_structure_and_sparse_case() -> None:
    result = derive_catalog(Path("dataset"))
    by_id = {item["testcase_id"]: item for item in result["testcases"]}

    assert result["dataset_id"] == "dataset-reference-2026"
    assert len(result["testcases"]) == 10
    assert by_id["TC-001"]["supported_gpus"]["value"] == ["GPU-A", "GPU-B", "GPU-C"]
    assert by_id["TC-005"]["supported_gpus"]["value"] == ["GPU-C"]

    first = by_id["TC-001"]
    assert first["timeout_seconds"]["value"] == 26
    assert first["pass_rate_badge"]["value"] == "degraded"
    assert first["pass_rate_badge"]["pass_rate_percent"] == 90.0
    assert first["last_measurement"]["value"] == "2025-12-05T18:00:00Z"

    sparse = by_id["TC-010"]
    assert sparse["timeout_seconds"]["value"] is None
    assert sparse["timeout_seconds"]["status"] == "insufficient-data"
    assert sparse["pass_rate_badge"]["value"] == "insufficient-data"
    assert sparse["timeout_seconds"]["evidence"] == {"GPU-C": {"samples": 5, "passed": 4}}


def test_every_derived_field_is_tied_to_the_pinned_snapshot() -> None:
    result = derive_catalog(Path("dataset"))

    for testcase in result["testcases"]:
        for field in (
            "supported_gpus",
            "timeout_seconds",
            "pass_rate_badge",
            "last_measurement",
        ):
            provenance = testcase[field]["provenance"]
            assert provenance["source_hash"] == result["source_hash"]
            assert provenance["computed_at"] == result["computed_at"]
            assert provenance["formula"]


def test_same_inputs_produce_identical_expected_state(tmp_path: Path) -> None:
    dataset_dir = tmp_path / "dataset"
    write_dataset(dataset_dir)

    assert derive_catalog(dataset_dir) == derive_catalog(dataset_dir)


def test_minimum_sample_rule_controls_sparse_pair(tmp_path: Path) -> None:
    rules_text = Path("rules.yaml").read_text(encoding="utf-8")
    rules_path = tmp_path / "rules.yaml"
    rules_path.write_text(
        rules_text.replace("minimum_samples_per_gpu: 10", "minimum_samples_per_gpu: 5"),
        encoding="utf-8",
    )

    result = derive_catalog(Path("dataset"), rules_path)
    sparse = next(item for item in result["testcases"] if item["testcase_id"] == "TC-010")

    assert sparse["timeout_seconds"]["status"] == "ok"
    assert sparse["timeout_seconds"]["value"] is not None
    assert sparse["pass_rate_badge"]["value"] == "degraded"
    assert sparse["pass_rate_badge"]["pass_rate_percent"] == 80.0


def test_derivation_rejects_dataset_with_broken_provenance(tmp_path: Path) -> None:
    dataset_dir = tmp_path / "dataset"
    write_dataset(dataset_dir)
    runs_path = dataset_dir / "runs.json"
    runs_path.write_text(runs_path.read_text(encoding="utf-8") + " ", encoding="utf-8")

    with pytest.raises(DerivationError, match="Dataset validation failed"):
        derive_catalog(dataset_dir)

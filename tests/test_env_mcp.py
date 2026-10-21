from pathlib import Path

import pytest

from env_mcp.service import EnvironmentQueryError, EnvironmentService


@pytest.fixture(scope="module")
def environment() -> EnvironmentService:
    return EnvironmentService(Path("dataset"))


def test_capability_matrix_contains_all_declared_entities(
    environment: EnvironmentService,
) -> None:
    result = environment.capability_matrix()

    assert result.dataset_id == "dataset-reference-2026"
    assert result.source_hash == (
        "83c9a22581b017a0ebc967d7c5bd4ef53f6c9edcb246e696ab402314a5eef394"
    )
    assert [gpu.gpu_id for gpu in result.gpus] == ["GPU-A", "GPU-B", "GPU-C"]
    assert len(result.testcases) == 10


@pytest.mark.parametrize(
    ("testcase_id", "expected"),
    [
        ("TC-001", ["GPU-A", "GPU-B", "GPU-C"]),
        ("TC-003", ["GPU-B", "GPU-C"]),
        ("TC-005", ["GPU-C"]),
        ("TC-010", ["GPU-C"]),
    ],
)
def test_supported_gpus_are_derived_from_capability_subsets(
    environment: EnvironmentService,
    testcase_id: str,
    expected: list[str],
) -> None:
    assert environment.supported_gpus(testcase_id).supported_gpus == expected


def test_unknown_testcase_resource_is_explicit(environment: EnvironmentService) -> None:
    with pytest.raises(EnvironmentQueryError, match="Unknown testcase_id"):
        environment.supported_gpus("TC-999")

"""Capability service behind the environment MCP resources."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from env_mcp.models import (
    CapabilityMatrixResult,
    GpuCapabilities,
    SupportedGpusResult,
    TestcaseRequirements,
)
from vgpu_catalog.snapshot import DEFAULT_DATASET_DIR, DatasetSnapshot, load_snapshot


class EnvironmentQueryError(ValueError):
    """Raised when a requested environment entity does not exist."""


def _supports(gpu: dict[str, Any], testcase: dict[str, Any]) -> bool:
    return set(testcase["required_capabilities"]).issubset(gpu["capabilities"])


class EnvironmentService:
    """Immutable in-memory view of one validated capability matrix."""

    def __init__(self, dataset_dir: Path = DEFAULT_DATASET_DIR) -> None:
        self.snapshot: DatasetSnapshot = load_snapshot(dataset_dir)
        self._gpus = sorted(
            self.snapshot.capabilities["gpus"],
            key=lambda item: item["gpu_id"],
        )
        self._testcases = {
            testcase["testcase_id"]: testcase
            for testcase in self.snapshot.capabilities["testcases"]
        }

    def capability_matrix(self) -> CapabilityMatrixResult:
        return CapabilityMatrixResult(
            dataset_id=self.snapshot.dataset_id,
            source_hash=self.snapshot.source_hash,
            snapshot_at=self.snapshot.snapshot_at,
            gpus=[GpuCapabilities.model_validate(gpu) for gpu in self._gpus],
            testcases=[
                TestcaseRequirements.model_validate(self._testcases[testcase_id])
                for testcase_id in sorted(self._testcases)
            ],
        )

    def supported_gpus(self, testcase_id: str) -> SupportedGpusResult:
        testcase = self._testcases.get(testcase_id)
        if testcase is None:
            raise EnvironmentQueryError(f"Unknown testcase_id: {testcase_id}")

        return SupportedGpusResult(
            dataset_id=self.snapshot.dataset_id,
            source_hash=self.snapshot.source_hash,
            snapshot_at=self.snapshot.snapshot_at,
            testcase_id=testcase_id,
            required_capabilities=testcase["required_capabilities"],
            supported_gpus=[gpu["gpu_id"] for gpu in self._gpus if _supports(gpu, testcase)],
        )

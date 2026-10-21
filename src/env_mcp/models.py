"""Structured environment resource models."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ResourceModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class GpuCapabilities(ResourceModel):
    gpu_id: str
    capabilities: list[str]


class TestcaseRequirements(ResourceModel):
    testcase_id: str
    required_capabilities: list[str]


class CapabilityMatrixResult(ResourceModel):
    dataset_id: str
    source_hash: str
    snapshot_at: str
    gpus: list[GpuCapabilities]
    testcases: list[TestcaseRequirements]


class SupportedGpusResult(ResourceModel):
    dataset_id: str
    source_hash: str
    snapshot_at: str
    testcase_id: str
    required_capabilities: list[str]
    supported_gpus: list[str]

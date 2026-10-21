"""Structured MCP result models for measurement queries."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ResultModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class TestcaseMeasurements(ResultModel):
    testcase_id: str
    gpus_with_measurements: list[str]


class TestcaseListResult(ResultModel):
    dataset_id: str
    source_hash: str
    snapshot_at: str
    testcases: list[TestcaseMeasurements]


class DurationStatsResult(ResultModel):
    dataset_id: str
    source_hash: str
    testcase_id: str
    gpu_id: str
    window_days: int = Field(ge=1)
    window_start: str
    window_end: str
    samples: int = Field(ge=0)
    passed: int = Field(ge=0)
    p50_seconds: float | None = Field(default=None, gt=0)
    p95_seconds: float | None = Field(default=None, gt=0)
    max_seconds: float | None = Field(default=None, gt=0)
    last_measurement: str | None


class PassRateResult(ResultModel):
    dataset_id: str
    source_hash: str
    testcase_id: str
    gpu_id: str
    window_days: int = Field(ge=1)
    window_start: str
    window_end: str
    samples: int = Field(ge=0)
    passed: int = Field(ge=0)
    failed: int = Field(ge=0)
    pass_rate_percent: float | None = Field(default=None, ge=0, le=100)
    last_measurement: str | None

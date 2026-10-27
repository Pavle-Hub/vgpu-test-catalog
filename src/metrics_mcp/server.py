"""MCP 2.x stdio server exposing pinned measurement tools."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Annotated

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import Field

from metrics_mcp.models import DurationStatsResult, PassRateResult, TestcaseListResult
from metrics_mcp.service import MetricsQueryError, MetricsService
from vgpu_catalog import __version__
from vgpu_catalog.snapshot import DEFAULT_DATASET_DIR

TestcaseId = Annotated[
    str,
    Field(pattern=r"^TC-[0-9]{3}$", description="Synthetic test-case identifier."),
]
GpuId = Annotated[
    str,
    Field(pattern=r"^GPU-[A-Z]$", description="Synthetic GPU identifier."),
]
WindowDays = Annotated[
    int,
    Field(ge=1, le=3650, description="Inclusive lookback window ending at snapshot time."),
]


def create_server(dataset_dir: Path = DEFAULT_DATASET_DIR) -> MCPServer:
    service = MetricsService(dataset_dir)
    server = MCPServer(
        name="metrics-mcp",
        title="Synthetic vGPU Metrics",
        description="Read-only statistics from a validated, pinned measurement snapshot.",
        instructions=(
            "Use these tools only for measurement statistics. Obtain compatibility "
            "from env-mcp resources and apply catalog policy from rules.yaml."
        ),
        version=__version__,
        subscriptions=False,
    )

    @server.tool(
        name="list_testcases",
        description="List test cases that exist in the pinned measurement snapshot.",
        structured_output=True,
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    def list_testcases() -> TestcaseListResult:
        return service.list_testcases()

    @server.tool(
        name="get_duration_stats",
        description="Return nearest-rank p50/p95 and maximum duration for one test/GPU pair.",
        structured_output=True,
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    def get_duration_stats(
        testcase_id: TestcaseId,
        gpu_id: GpuId,
        window_days: WindowDays = 30,
    ) -> DurationStatsResult:
        try:
            return service.get_duration_stats(testcase_id, gpu_id, window_days)
        except MetricsQueryError as error:
            raise ToolError(str(error)) from error

    @server.tool(
        name="get_pass_rate",
        description="Return pass/fail counts and pass percentage for one test/GPU pair.",
        structured_output=True,
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    def get_pass_rate(
        testcase_id: TestcaseId,
        gpu_id: GpuId,
        window_days: WindowDays = 30,
    ) -> PassRateResult:
        try:
            return service.get_pass_rate(testcase_id, gpu_id, window_days)
        except MetricsQueryError as error:
            raise ToolError(str(error)) from error

    return server


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_DIR)
    args = parser.parse_args()

    create_server(args.dataset).run(transport="stdio")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

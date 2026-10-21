import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters, stdio_client

PROJECT_ROOT = Path(__file__).parents[1].resolve()
DATASET_DIR = PROJECT_ROOT / "dataset"


async def _metrics_round_trip() -> None:
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "metrics_mcp.server", "--dataset", str(DATASET_DIR)],
        cwd=PROJECT_ROOT,
    )
    async with (
        stdio_client(parameters) as (read_stream, write_stream),
        ClientSession(read_stream, write_stream) as session,
    ):
        await session.initialize()
        tools = await session.list_tools()
        assert [tool.name for tool in tools.tools] == [
            "list_testcases",
            "get_duration_stats",
            "get_pass_rate",
        ]
        duration_tool = next(tool for tool in tools.tools if tool.name == "get_duration_stats")
        assert duration_tool.input_schema["properties"]["testcase_id"]["pattern"] == (
            "^TC-[0-9]{3}$"
        )
        assert duration_tool.input_schema["properties"]["window_days"]["minimum"] == 1
        assert duration_tool.input_schema["properties"]["window_days"]["maximum"] == 3650

        result = await session.call_tool(
            "get_duration_stats",
            {"testcase_id": "TC-001", "gpu_id": "GPU-A", "window_days": 30},
        )
        assert not result.is_error
        assert result.structured_content["samples"] == 30
        assert result.structured_content["p95_seconds"] == 18.395

        error_result = await session.call_tool(
            "get_duration_stats",
            {"testcase_id": "TC-999", "gpu_id": "GPU-A"},
        )
        assert error_result.is_error
        assert "Unknown testcase_id" in error_result.content[0].text


async def _environment_round_trip() -> None:
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "env_mcp.server", "--dataset", str(DATASET_DIR)],
        cwd=PROJECT_ROOT,
    )
    async with (
        stdio_client(parameters) as (read_stream, write_stream),
        ClientSession(read_stream, write_stream) as session,
    ):
        await session.initialize()
        resources = await session.list_resources()
        assert [str(resource.uri) for resource in resources.resources] == [
            "vgpu-env://capability-matrix"
        ]

        templates = await session.list_resource_templates()
        assert [template.uri_template for template in templates.resource_templates] == [
            "vgpu-env://testcases/{testcase_id}/supported-gpus"
        ]

        result = await session.read_resource("vgpu-env://testcases/TC-006/supported-gpus")
        content = json.loads(result.contents[0].text)
        assert content["supported_gpus"] == ["GPU-B", "GPU-C"]
        assert content["source_hash"] == (
            "83c9a22581b017a0ebc967d7c5bd4ef53f6c9edcb246e696ab402314a5eef394"
        )


def test_metrics_mcp_stdio_protocol_round_trip() -> None:
    asyncio.run(_metrics_round_trip())


def test_environment_mcp_stdio_protocol_round_trip() -> None:
    asyncio.run(_environment_round_trip())

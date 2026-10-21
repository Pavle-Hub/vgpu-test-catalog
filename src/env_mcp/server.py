"""MCP 2.x stdio server exposing pinned environment resources."""

from __future__ import annotations

import argparse
from pathlib import Path

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ResourceNotFoundError

from env_mcp.service import EnvironmentQueryError, EnvironmentService
from vgpu_catalog import __version__
from vgpu_catalog.snapshot import DEFAULT_DATASET_DIR


def create_server(dataset_dir: Path = DEFAULT_DATASET_DIR) -> MCPServer:
    service = EnvironmentService(dataset_dir)
    server = MCPServer(
        name="env-mcp",
        title="Synthetic vGPU Environment",
        description="Read-only capability resources from a validated, pinned snapshot.",
        instructions=(
            "Read the capability matrix or a supported-GPU resource. Do not infer "
            "compatibility from measurement presence."
        ),
        version=__version__,
        subscriptions=False,
    )

    @server.resource(
        "vgpu-env://capability-matrix",
        name="capability-matrix",
        title="vGPU capability matrix",
        description="All GPU capabilities and test-case requirements.",
        mime_type="application/json",
    )
    def capability_matrix() -> str:
        return service.capability_matrix().model_dump_json(indent=2)

    @server.resource(
        "vgpu-env://testcases/{testcase_id}/supported-gpus",
        name="supported-gpus",
        title="Supported GPUs for a test case",
        description="GPU identifiers whose capabilities satisfy every test requirement.",
        mime_type="application/json",
    )
    def supported_gpus(testcase_id: str) -> str:
        try:
            return service.supported_gpus(testcase_id).model_dump_json(indent=2)
        except EnvironmentQueryError as error:
            raise ResourceNotFoundError(str(error)) from error

    return server


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_DIR)
    args = parser.parse_args()

    create_server(args.dataset).run(transport="stdio")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

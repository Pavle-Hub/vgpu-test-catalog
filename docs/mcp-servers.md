# MCP servers

The demonstration composes two read-only MCP 2.x stdio servers. Both load and
fully validate the repository-pinned dataset before accepting requests, and
every response carries the same dataset ID, snapshot timestamp, and source hash.

## `metrics-mcp`: tools

Measurement queries are operations with validated arguments, so they are
exposed as MCP tools with structured input and output schemas.

| Tool | Purpose |
| --- | --- |
| `list_testcases()` | Lists test cases and GPUs that have measurements. |
| `get_duration_stats(testcase_id, gpu_id, window_days=30)` | Returns nearest-rank p50/p95, maximum duration, sample count, passed count, and last measurement. |
| `get_pass_rate(testcase_id, gpu_id, window_days=30)` | Returns passed/failed counts, pass percentage, and last measurement. |

The service returns zero samples and `null` statistics for a known pair with no
measurements. Unknown identifiers and windows outside 1-3650 days are explicit
tool errors. Passed/failed counts are authoritative; the percentage is an
unrounded convenience value. Metrics are raw evidence, so confidence and display
rounding remain in `rules.yaml` and are not duplicated inside the server.

## `env-mcp`: resources

Environment facts are addressable data rather than operations, so they are MCP
resources.

| Resource | Purpose |
| --- | --- |
| `vgpu-env://capability-matrix` | Static JSON resource containing all GPU capabilities and test requirements. |
| `vgpu-env://testcases/{testcase_id}/supported-gpus` | Resource template deriving compatible GPUs by capability-set inclusion. |

Measurement presence never implies support. A GPU is returned only when every
required test capability exists in that GPU's capability set.

## Launch commands

The commands below start stdio servers and therefore wait for an MCP client; they
are not interactive terminal applications.

```powershell
metrics-mcp --dataset dataset
env-mcp --dataset dataset
```

Equivalent module commands are:

```powershell
python -m metrics_mcp.server --dataset dataset
python -m env_mcp.server --dataset dataset
```

## Protocol verification

The integration tests launch both servers as child processes and use the MCP SDK
client to perform a real initialize/list/call/read lifecycle:

```powershell
python -m pytest tests/test_mcp_stdio.py
```

Service tests separately verify statistics, capability subset logic, invalid
queries, empty measurement pairs, and snapshot provenance.

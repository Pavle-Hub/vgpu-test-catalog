import copy
import json
from pathlib import Path

import pytest

from vgpu_catalog.hashing import sha256_bytes
from vgpu_eval.codex_batch import (
    ROOT,
    BatchError,
    audit_events,
    load_config,
    make_plan,
    write_analysis,
    write_json,
)
from vgpu_eval.codex_reanalysis import reanalyze


def saved_collection(source: Path, *, exclusion: bool = True) -> Path:
    plan = make_plan(load_config(ROOT / "eval/codex-protocol.yaml"))
    row = next(r for r in plan if r["mode"] == "without-checker")
    directory = source / "runs" / row["run_id"] / "attempt-01"
    directory.mkdir(parents=True)
    events = [
        {"type": "item.completed", "item": {
            "type": "mcp_tool_call", "server": server, "tool": tool,
            "status": "completed", "arguments": {}, "error": None,
        }}
        for server, tool in (
            ("env-mcp", "read_resource"), ("metrics-mcp", "get_duration_stats"),
            ("metrics-mcp", "get_pass_rate"),
        )
    ]
    events += [
        {"type": "item.completed", "item": {
            "type": "command_execution",
            "command": "rg --files -g '!dataset/runs.json'" if exclusion
            else "Get-Content dataset/runs.json",
        }},
        {"type": "turn.completed", "usage": {}},
    ]
    audit = audit_events(events, row["mode"])
    original_audit = copy.deepcopy(audit)
    original_audit["violations"] = ["direct-source-data-read"]
    result = {
        **row, "status": "completed", "success": False, "checker_valid": True,
        "protected_fields_preserved": True, "scope_preserved": True,
        "changed_paths": ["catalog/test_catalog.md"], "checker_attempts": 0,
        "evidence_read": True, "violations": ["direct-source-data-read"], "usage": {},
        "baseline_sha256": sha256_bytes(b"baseline"),
        "output_sha256": sha256_bytes(b"output"),
    }
    (directory / "baseline.md").write_bytes(b"baseline")
    (directory / "agent-output.md").write_bytes(b"output")
    (directory / "events.jsonl").write_text(
        "\n".join(json.dumps(e) for e in events), encoding="utf-8"
    )
    write_json(directory / "audit.json", original_audit)
    write_json(directory / "result.json", result)
    write_json(directory / "final-checker.json", {"valid": True})
    write_json(source / "plan.json", plan)
    write_json(source / "frozen-protocol.json", {"identity": {"plan": plan, "head": "frozen"}})
    write_analysis(source, plan)
    return directory


@pytest.mark.parametrize("exclusion", [True, False])
def test_reanalysis_preserves_originals_and_only_corrects_exclusions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, exclusion: bool,
) -> None:
    source, destination = tmp_path / "source", tmp_path / "revision"
    directory = saved_collection(source, exclusion=exclusion)
    before = {p: p.read_bytes() for p in source.rglob("*") if p.is_file()}
    monkeypatch.setattr(
        "subprocess.Popen", lambda *a, **kw: pytest.fail("No agent or subprocess is needed")
    )
    summary = reanalyze(source, destination)
    assert summary["groups"]["fault/without-checker"]["successes"] == int(exclusion)
    revised = json.loads(
        (destination / directory.relative_to(source) / "result.json").read_text()
    )
    assert revised["success"] == exclusion
    assert revised["original_success"] is False
    assert all(path.read_bytes() == data for path, data in before.items())
    correction = json.loads((destination / "correction.json").read_text())
    assert len(correction["changed_attempts"]) == int(exclusion)
    assert correction["no_agent_sessions_invoked"] is True
    with pytest.raises(BatchError, match="already exists"):
        reanalyze(source, destination)


def test_reanalysis_refuses_changed_evidence_before_writing_output(tmp_path: Path) -> None:
    source, destination = tmp_path / "source", tmp_path / "revision"
    directory = saved_collection(source)
    (directory / "agent-output.md").write_bytes(b"tampered")
    with pytest.raises(BatchError, match="hash mismatch"):
        reanalyze(source, destination)
    assert not destination.exists()

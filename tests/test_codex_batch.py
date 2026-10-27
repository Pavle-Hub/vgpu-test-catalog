import copy
import json
import sys
from pathlib import Path

import pytest

from vgpu_eval.codex_batch import (
    ROOT,
    analyze,
    audit_events,
    cli_command,
    find_codex,
    git,
    load_config,
    make_plan,
    prepare_workspace,
    run_case,
    wilson,
    write_analysis,
    write_json,
)


def configuration() -> dict:
    return load_config(ROOT / "eval/codex-protocol.yaml")


def test_cli_discovery_falls_back_to_desktop_installation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cli = tmp_path / "AppData/Local/OpenAI/Codex/bin/build-id/codex.exe"
    cli.parent.mkdir(parents=True)
    cli.touch()
    monkeypatch.setattr("vgpu_eval.codex_batch.shutil.which", lambda _: None)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.delenv("CODEX_CLI_PATH", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "sandbox-redirect"))
    monkeypatch.setattr(
        "vgpu_eval.codex_batch.subprocess.check_output",
        lambda *args, **kwargs: "codex-cli test-version\n",
    )

    path, version = find_codex("test-version")
    assert Path(path) == cli.resolve()
    assert version == "codex-cli test-version"


def test_explicit_cli_does_not_fall_back_to_another_installation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "vgpu_eval.codex_batch.shutil.which",
        lambda _: pytest.fail("Explicit selection must not search PATH"),
    )
    with pytest.raises(ValueError, match="was not found"):
        find_codex("test-version", tmp_path / "missing.exe")


def test_cli_discovery_rejects_wrong_version(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cli = tmp_path / "codex.exe"
    cli.touch()
    monkeypatch.setattr(
        "vgpu_eval.codex_batch.subprocess.check_output",
        lambda *args, **kwargs: "codex-cli other-version\n",
    )
    with pytest.raises(ValueError, match="installed versions differ"):
        find_codex("test-version", cli)


def evidence_events() -> list[dict]:
    calls = [
        ("env-mcp", "read_resource"),
        ("metrics-mcp", "get_duration_stats"),
        ("metrics-mcp", "get_pass_rate"),
    ]
    events = [
        {
            "type": "item.completed",
            "item": {
                "type": "mcp_tool_call",
                "server": server,
                "tool": tool,
                "status": "completed",
                "arguments": {},
                "error": None,
            },
        }
        for server, tool in calls
    ]
    return events + [{"type": "turn.completed", "usage": {"input_tokens": 100}}]


def test_plan_has_complete_reproducible_counterbalanced_pairs() -> None:
    config = configuration()
    plan = make_plan(config)
    assert plan == make_plan(config)
    assert len(plan) == 60
    assert len({row["run_id"] for row in plan}) == 60
    assert sum(row["condition"] == "clean" for row in plan) == 10
    starts = []
    for first, second in zip(plan[::2], plan[1::2], strict=True):
        assert first["pair_id"] == second["pair_id"]
        assert first["fault_class"] == second["fault_class"]
        assert first["testcase_id"] == second["testcase_id"]
        assert {first["mode"], second["mode"]} == {"with-checker", "without-checker"}
        starts.append(first["mode"])
    assert starts.count("with-checker") == starts.count("without-checker") == 15


def test_export_history_contains_fault_and_excludes_prior_results(tmp_path: Path) -> None:
    row = next(row for row in make_plan(configuration()) if row["condition"] == "fault")
    workspace, baseline, before = prepare_workspace(row, tmp_path / "case")

    assert not (workspace / "eval/results").exists()
    assert not (workspace / "eval/protocol-v3.yaml").exists()
    assert (workspace / ".agents/skills/sync-catalog/SKILL.md").is_file()
    assert git("show", "HEAD:catalog/test_catalog.md", cwd=workspace) != baseline.decode().strip()
    assert len(git("rev-list", "HEAD", cwd=workspace).splitlines()) == 1
    assert "catalog/test_catalog.md" in before


def test_cli_pins_model_effort_and_requires_both_local_servers(tmp_path: Path) -> None:
    config = configuration()
    command = cli_command("codex", tmp_path, config, tmp_path / "final.txt")

    assert "--ignore-user-config" in command
    assert "--ephemeral" in command
    assert "workspace-write" in command
    assert command[command.index("--model") + 1] == config["agent"]["model"]
    assert 'approval_policy="on-request"' in command
    assert any(arg.endswith('.trust_level="trusted"') for arg in command)
    if sys.platform == "win32":
        assert 'windows.sandbox="elevated"' in command
    assert "mcp_servers.env-mcp.required=true" in command
    assert "mcp_servers.metrics-mcp.required=true" in command
    assert 'mcp_servers.metrics-mcp.tools.get_duration_stats.approval_mode="approve"' in command


def test_audit_counts_each_checker_invocation_and_rejects_without_mode() -> None:
    events = evidence_events() + [
        {
            "type": "item.completed",
            "item": {
                "type": "command_execution",
                "command": (
                    "python -m catalog_check.cli --check; python -m catalog_check.cli --check"
                ),
            },
        }
    ]
    with_checker = audit_events(events, "with-checker")
    assert with_checker["checker_attempts"] == 2
    assert with_checker["evidence_read"]
    assert not with_checker["violations"]
    without = audit_events(events, "without-checker")
    assert "checker-used-in-without-checker-mode" in without["violations"]


def test_audit_rejects_missing_sources_and_deterministic_oracles() -> None:
    events = [
        {
            "type": "item.completed",
            "item": {
                "type": "command_execution",
                "command": "python -m catalog_check.cli --write",
            },
        }
    ]
    audit = audit_events(events, "with-checker")
    assert not audit["turn_completed"]
    assert "deterministic-writer-or-derivation-command" in audit["violations"]
    assert "missing-auditable-MCP-evidence" in audit["violations"]


def test_clean_controls_and_interrupted_attempts_do_not_inflate_repair_rates() -> None:
    plan = make_plan(configuration())
    pair = [row for row in plan if row["pair_id"] == "wrong-value-r01"]
    results = [
        {**row, "status": "completed", "success": row["mode"] == "with-checker"} for row in pair
    ]
    clean = next(row for row in plan if row["condition"] == "clean")
    results.append({**clean, "status": "completed", "success": True})
    interrupted = copy.deepcopy(results[0])
    interrupted["status"] = "interrupted"
    results.append(interrupted)

    summary = analyze(results, 60)
    assert summary["completed_runs"] == 3
    assert summary["interrupted_attempts"] == 1
    assert not summary["complete"]
    assert summary["groups"]["fault/with-checker"]["n"] == 1
    assert summary["paired"]["fault"]["with_only"] == 1
    assert summary["paired"]["fault"]["paired_rate_difference"] == 1
    assert summary["paired"]["clean"]["complete_pairs"] == 0


def test_empty_analysis_is_unmeasured_not_a_zero_success_claim() -> None:
    summary = analyze([], 60)
    assert summary["groups"]["fault/with-checker"]["rate"] is None
    assert summary["groups"]["fault/with-checker"]["wilson_95"] is None
    assert wilson(0, 0) is None
    lower, upper = wilson(5, 5)
    assert 0.56 < lower < 0.57
    assert upper == pytest.approx(1)


def test_summary_rejects_duplicate_completed_results(tmp_path: Path) -> None:
    plan = make_plan(configuration())
    row = {**plan[0], "status": "completed", "success": True, "checker_attempts": 1}
    for attempt in ("attempt-01", "attempt-02"):
        write_json(tmp_path / "runs" / row["run_id"] / attempt / "result.json", row)
    with pytest.raises(ValueError, match="Duplicate completed run"):
        write_analysis(tmp_path, plan)


def test_report_preserves_incomplete_status(tmp_path: Path) -> None:
    summary = write_analysis(tmp_path, make_plan(configuration()))
    assert summary["completed_runs"] == 0
    persisted = json.loads((tmp_path / "summary.json").read_text())
    assert persisted["complete"] is False
    assert "not measured" in (tmp_path / "report.md").read_text()


def test_failed_client_start_is_preserved_as_unscored_interruption(tmp_path: Path) -> None:
    config = configuration()
    row = make_plan(config)[0]
    baseline = (ROOT / "catalog/test_catalog.md").read_bytes()

    # Python deliberately rejects CLI-specific flags; no model is invoked.
    result = run_case(sys.executable, config, row, tmp_path / "failed-client")

    assert result["status"] == "interrupted"
    assert result["returncode"] != 0
    assert not result["success"]
    assert (tmp_path / "failed-client/stderr.txt").stat().st_size > 0
    assert (tmp_path / "failed-client/result.json").is_file()
    assert analyze([result], 60)["completed_runs"] == 0
    assert (ROOT / "catalog/test_catalog.md").read_bytes() == baseline


def test_policy_block_is_interruption_even_when_cli_returns_zero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class PolicyBlockedProcess:
        def __init__(self, *args, **kwargs):
            kwargs["stdout"].write(b'{"type":"turn.completed","usage":{}}\n')
            kwargs["stderr"].write(
                b"ERROR tools::router: exec_command failed: "
                b"CreateProcess rejected: blocked by policy\n"
            )

        def wait(self, timeout=None):
            return 0

    # Prepare before mocking: git also uses Popen internally.
    config = configuration()
    row = make_plan(config)[0]
    prepared = prepare_workspace(row, tmp_path / "input")
    monkeypatch.setattr("vgpu_eval.codex_batch.subprocess.Popen", PolicyBlockedProcess)
    monkeypatch.setattr(
        "vgpu_eval.codex_batch.prepare_workspace",
        lambda row, directory, **kwargs: prepared,
    )
    result = run_case("codex", config, row, tmp_path / "attempt")

    assert result["returncode"] == 0
    assert result["status"] == "interrupted"
    assert result["infrastructure_issues"] == ["command-execution-blocked-by-policy"]


def test_audit_classifies_mcp_approval_and_runtime_access_as_infrastructure() -> None:
    events = [
        {
            "type": "item.completed",
            "item": {
                "type": "command_execution",
                "command": "python -m vgpu_catalog.validation dataset",
                "exit_code": 1,
                "aggregated_output": "did not find executable: Access is denied.",
            },
        },
        {
            "type": "item.completed",
            "item": {
                "type": "mcp_tool_call",
                "server": "metrics-mcp",
                "tool": "list_testcases",
                "status": "failed",
                "error": {
                    "message": "MCP tool call requires approval, but approval policy is never",
                },
            },
        },
    ]
    audit = audit_events(events, "without-checker")
    assert audit["infrastructure_issues"] == ["mcp-approval-required", "runtime-access-denied"]

"""Isolated Codex CLI experiments with auditable transcripts and paired analysis."""

from __future__ import annotations

import argparse
import csv
import importlib.metadata
import json
import math
import os
import random
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from catalog_check.checker import check_catalog
from vgpu_catalog.hashing import pretty_json_bytes, sha256_bytes
from vgpu_eval.faults import FaultClass, inject_fault
from vgpu_eval.runs import _protected_fields

ROOT = Path(__file__).resolve().parents[2]
EXPORTED_ROOTS = {"src", "schemas", "dataset", "catalog", ".agents", ".cursor"}
EXPORTED_FILES = {"rules.yaml", "pyproject.toml", "requirements.lock"}
MODES = ("with-checker", "without-checker")


class BatchError(ValueError):
    """An experiment cannot proceed with a trustworthy configuration."""


def find_codex(expected_version: str, explicit: Path | None = None) -> tuple[str, str]:
    """Find a matching CLI on PATH or in the standard local app installation."""

    candidates: list[Path] = []
    if explicit is not None:
        candidates.append(explicit)
    else:
        on_path = shutil.which("codex")
        if on_path:
            candidates.append(Path(on_path))
        supplied = os.environ.get("CODEX_CLI_PATH")
        if supplied:
            candidates.append(Path(supplied))
        local_roots = [Path.home() / "AppData/Local"]
        if os.environ.get("LOCALAPPDATA"):
            local_roots.append(Path(os.environ["LOCALAPPDATA"]))
        for local in local_roots:
            desktop_bin = local / "OpenAI/Codex/bin"
            if desktop_bin.is_dir():
                candidates.extend(sorted(desktop_bin.glob("*/codex.exe")))
            candidates.append(local / "Programs/OpenAI/Codex/codex.exe")

    seen: set[Path] = set()
    found: list[str] = []
    for candidate in candidates:
        candidate = candidate.resolve()
        if candidate in seen or not candidate.is_file():
            continue
        seen.add(candidate)
        try:
            version = subprocess.check_output(
                [str(candidate), "--version"],
                text=True,
                timeout=10,
                stderr=subprocess.PIPE,
            ).strip()
        except (OSError, subprocess.SubprocessError):
            continue
        if version == f"codex-cli {expected_version}":
            return str(candidate), version
        found.append(f"{candidate}: {version}")
    if found:
        raise BatchError(
            f"Need Codex CLI {expected_version}; installed versions differ: " + "; ".join(found)
        )
    raise BatchError(
        "Codex CLI was not found on PATH or in its local installation. "
        "Supply its executable with --codex C:/path/to/codex.exe."
    )


def now() -> str:
    return datetime.now(UTC).isoformat()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(pretty_json_bytes(value))


def git(*args: str, cwd: Path = ROOT) -> str:
    result = subprocess.run(
        ["git", "-C", str(cwd), *args], capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def tracked_hashes() -> dict[str, str]:
    return {
        name: sha256_bytes((ROOT / name).read_bytes())
        for name in git("ls-files", "-z").split("\0")
        if name
    }


def ensure_runtime(output: Path) -> Path:
    """Copy the existing Windows Python runtime out of sandbox-restricted AppData."""

    if sys.platform != "win32":
        return Path(sys.executable).resolve()
    runtime = output / "python-runtime"
    marker = runtime / "runtime-identity.json"
    identity = {
        "python": sys.version,
        "base_executable_sha256": sha256_bytes(Path(sys._base_executable).read_bytes()),
        "requirements_sha256": sha256_bytes((ROOT / "requirements.lock").read_bytes()),
        "packages": sorted(
            (d.metadata["Name"], d.version)
            for d in importlib.metadata.distributions()
            if d.metadata.get("Name")
        ),
    }
    # JSON arrays make the persisted representation equal on subsequent runs.
    identity = json.loads(json.dumps(identity))
    if marker.is_file():
        if json.loads(marker.read_text(encoding="utf-8")) != identity:
            raise BatchError(
                "Python environment changed; use a new output directory and repeat pilot."
            )
        return runtime / "python.exe"
    if runtime.exists():
        raise BatchError(f"Incomplete runtime exists at {runtime}; use a new --output directory.")
    runtime.mkdir(parents=True)
    base = Path(sys.base_prefix)
    for pattern in ("python*.exe", "*.dll"):
        for source in base.glob(pattern):
            shutil.copyfile(source, runtime / source.name)
    for folder in ("Lib", "DLLs"):
        shutil.copytree(
            base / folder,
            runtime / folder,
            ignore=shutil.ignore_patterns("site-packages", "__pycache__"),
        )
    shutil.copytree(
        Path(sys.prefix) / "Lib/site-packages",
        runtime / "Lib/site-packages",
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    python = runtime / "python.exe"
    probe = subprocess.run(
        [str(python), "-B", "-c", "import mcp, yaml, catalog_check.cli; print('runtime-ok')"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if probe.returncode != 0:
        raise BatchError(f"Copied Python runtime failed verification: {probe.stderr}")
    write_json(marker, identity)
    return python


def make_plan(config: dict[str, Any]) -> list[dict[str, Any]]:
    design = config["design"]
    pairs: list[dict[str, Any]] = []
    for case in design["fault_cases"]:
        for repetition in range(1, design["repetitions"] + 1):
            pairs.append({"condition": "fault", "repetition": repetition, **case})
    for repetition in range(1, design["clean_pairs"] + 1):
        pairs.append(
            {"condition": "clean", "fault_class": "", "testcase_id": "", "repetition": repetition}
        )
    random.Random(design["seed"]).shuffle(pairs)
    rows = []
    for index, pair in enumerate(pairs):
        subject = pair["fault_class"] or "clean"
        pair_id = f"{subject}-r{pair['repetition']:02d}"
        modes = MODES if index % 2 == 0 else tuple(reversed(MODES))
        for mode in modes:
            rows.append(
                {
                    **pair,
                    "order": len(rows) + 1,
                    "pair_id": pair_id,
                    "mode": mode,
                    "run_id": f"ce1-{pair_id}-{mode}",
                }
            )
    return rows


def load_config(path: Path) -> dict[str, Any]:
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(config, dict) or config.get("protocol_id") != "codex-agent-eval-1":
        raise BatchError("Unsupported Codex protocol.")
    design = config["design"]
    if tuple(design["modes"]) != MODES:
        raise BatchError("The protocol must define both paired modes in the expected order.")
    if {case["fault_class"] for case in design["fault_cases"]} != {f.value for f in FaultClass}:
        raise BatchError("The protocol must include all five fault classes.")
    if design["repetitions"] < 1 or design["clean_pairs"] < 1:
        raise BatchError("At least one repetition and clean pair are required.")
    return config


def inventory(workspace: Path) -> dict[str, str]:
    result = {}
    for path in workspace.rglob("*"):
        rel = path.relative_to(workspace)
        if any(part in {".git", "__pycache__", ".pytest_cache", ".tmp"} for part in rel.parts):
            continue
        if path.is_file():
            result[rel.as_posix()] = sha256_bytes(path.read_bytes())
    return result


def prepare_workspace(
    row: dict[str, Any],
    directory: Path,
    runtime_python: Path | None = None,
) -> tuple[Path, bytes, dict[str, str]]:
    workspace = directory / "workspace"
    workspace.mkdir(parents=True, exist_ok=False)
    for name in git("ls-files", "-z").split("\0"):
        if not name:
            continue
        relative = Path(name)
        if relative.parts[0] not in EXPORTED_ROOTS and name not in EXPORTED_FILES:
            continue
        # Cursor MCP config contains workspace variables that do not apply to Codex.
        if name == ".cursor/mcp.json":
            continue
        target = workspace / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    python = str(runtime_python or Path(sys.executable).resolve())
    config_lines = []
    for server, module in (("env-mcp", "env_mcp.server"), ("metrics-mcp", "metrics_mcp.server")):
        config_lines.extend(
            [
                f'[mcp_servers."{server}"]',
                f"command = {json.dumps(python)}",
                f"args = {json.dumps(['-m', module, '--dataset', str(workspace / 'dataset')])}",
                f"cwd = {json.dumps(str(workspace))}",
                "required = true",
                "",
            ]
        )
    (workspace / ".codex").mkdir()
    (workspace / ".codex/config.toml").write_bytes("\n".join(config_lines).encode("utf-8"))
    catalog = workspace / "catalog/test_catalog.md"
    baseline = catalog.read_bytes()
    write_json(directory / "case.json", row)
    (directory / "baseline.md").write_bytes(baseline)
    if row["condition"] == "fault":
        faulty, injection = inject_fault(
            baseline.decode("utf-8"),
            row["fault_class"],
            row["testcase_id"],
            workspace / "rules.yaml",
        )
        catalog.write_bytes(faulty.encode("utf-8"))
        write_json(directory / "injection.json", injection.as_dict())
    initial = check_catalog(catalog, workspace / "dataset", workspace / "rules.yaml")
    if initial.valid != (row["condition"] == "clean"):
        raise BatchError("Input did not have the expected clean/faulty state.")
    write_json(directory / "initial-checker.json", initial.as_dict())
    (directory / "input.md").write_bytes(catalog.read_bytes())
    git("init", "--quiet", cwd=workspace)
    git("config", "core.autocrlf", "false", cwd=workspace)
    git("add", ".", cwd=workspace)
    git(
        "-c",
        "user.name=Experiment",
        "-c",
        "user.email=experiment@example.invalid",
        "commit",
        "--quiet",
        "-m",
        "Injected experiment input",
        cwd=workspace,
    )
    return workspace, baseline, inventory(workspace)


def cli_command(
    cli: str,
    workspace: Path,
    config: dict[str, Any],
    final: Path,
    runtime_python: Path | None = None,
) -> list[str]:
    python = str(runtime_python or Path(sys.executable).resolve())
    command = [
        cli,
        "--no-daemon",
        "exec",
        "--ignore-user-config",
        "--ephemeral",
        "--json",
        "--color",
        "never",
        "--sandbox",
        "workspace-write",
        "-C",
        str(workspace),
        "--model",
        config["agent"]["model"],
        "-c",
        f'model_reasoning_effort="{config["agent"]["reasoning_effort"]}"',
        "-c",
        'approval_policy="on-request"',
        "-c",
        f'projects.{json.dumps(str(workspace.resolve()))}.trust_level="trusted"',
        "-o",
        str(final),
    ]
    if sys.platform == "win32":
        command.extend(["-c", 'windows.sandbox="elevated"'])
    for server, module in (("env-mcp", "env_mcp.server"), ("metrics-mcp", "metrics_mcp.server")):
        values = {
            "command": python,
            "args": ["-m", module, "--dataset", str(workspace / "dataset")],
            "cwd": str(workspace),
            "startup_timeout_sec": 30,
            "required": True,
        }
        for key, value in values.items():
            command.extend(["-c", f"mcp_servers.{server}.{key}={json.dumps(value)}"])
    for tool in ("list_testcases", "get_duration_stats", "get_pass_rate"):
        command.extend(["-c", f'mcp_servers.metrics-mcp.tools.{tool}.approval_mode="approve"'])
    return command


def sandbox_preflight(cli: str, workspace: Path, python: Path, directory: Path) -> bool:
    """Check interpreter execution and catalog-directory writes without a model call."""

    if sys.platform != "win32":
        return True
    code = (
        "import mcp, yaml, catalog_check.cli; from pathlib import Path; "
        "p=Path('catalog/.runtime-probe'); p.write_text('ok'); p.unlink(); "
        "print('sandbox-runtime-ok')"
    )
    args = [
        cli,
        "-C",
        str(workspace),
        "-c",
        'windows.sandbox="elevated"',
        "-c",
        'sandbox_mode="workspace-write"',
        "sandbox",
        str(python),
        "-B",
        "-c",
        code,
    ]
    result = subprocess.run(args, cwd=workspace, capture_output=True, timeout=120, check=False)
    (directory / "sandbox-preflight.stdout.txt").write_bytes(result.stdout)
    (directory / "sandbox-preflight.stderr.txt").write_bytes(result.stderr)
    return result.returncode == 0 and b"sandbox-runtime-ok" in result.stdout


def audit_events(events: list[dict[str, Any]], mode: str) -> dict[str, Any]:
    commands: list[str] = []
    infrastructure_issues: list[str] = []
    calls: list[dict[str, Any]] = []
    completed = False
    usage: dict[str, Any] = {}
    for event in events:
        if event.get("type") == "turn.completed":
            completed = True
            usage = event.get("usage", {})
        if event.get("type") != "item.completed":
            continue
        item = event.get("item", {})
        if item.get("type") == "command_execution":
            commands.append(str(item.get("command", "")))
            output = str(item.get("aggregated_output", ""))
            if item.get("exit_code") not in (None, 0) and "Access is denied" in output:
                infrastructure_issues.append("runtime-access-denied")
        if item.get("type") == "mcp_tool_call":
            if "requires approval" in json.dumps(item.get("error")):
                infrastructure_issues.append("mcp-approval-required")
            calls.append(
                {key: item.get(key) for key in ("server", "tool", "arguments", "status", "error")}
            )
    checker_attempts = sum(
        len(re.findall(r"(?:catalog_check(?:\.cli|\.py)?|catalog-check)\b[^;\r\n]*?--check\b", cmd))
        for cmd in commands
    )
    violations = []
    for cmd in commands:
        if re.search(
            r"(?:catalog_check(?:\.cli|\.py)?|catalog-check).*?--write|derive.catalog|write_catalog",
            cmd,
        ):
            violations.append("deterministic-writer-or-derivation-command")
        if re.search(r"\bpytest\b|vgpu_catalog\.derivation|catalog_check\.checker", cmd):
            violations.append("oracle-source-or-tests-used")
        if re.search(r"dataset[/\\]+(?:runs|capabilities)\.json", cmd):
            violations.append("direct-source-data-read")
        if re.search(r"\bgit\s+(?:show|restore|checkout|reset)\b", cmd):
            violations.append("history-recovery-command")
    attempts = checker_attempts
    if mode == "without-checker" and attempts:
        violations.append("checker-used-in-without-checker-mode")
    if mode == "with-checker" and not 1 <= attempts <= 3:
        violations.append("checker-attempt-budget-violation")
    successful = [
        call for call in calls if call.get("status") == "completed" and not call.get("error")
    ]
    # Hosts may expose MCP resources through generic resource helpers. Preserve
    # arguments as well, so an env-mcp resource read is attributable in the audit.
    env_evidence = any(
        call.get("tool") in {"read_resource", "read_mcp_resource"}
        and (call.get("server") == "env-mcp" or "env-mcp" in json.dumps(call.get("arguments")))
        for call in successful
    )
    metrics_tools = {call.get("tool") for call in successful if call.get("server") == "metrics-mcp"}
    evidence_read = env_evidence and {"get_duration_stats", "get_pass_rate"}.issubset(metrics_tools)
    if not evidence_read:
        violations.append("missing-auditable-MCP-evidence")
    return {
        "turn_completed": completed,
        "checker_attempts": attempts,
        "evidence_read": evidence_read,
        "violations": sorted(set(violations)),
        "commands": commands,
        "mcp_calls": calls,
        "usage": usage,
        "infrastructure_issues": sorted(set(infrastructure_issues)),
        "audit_limit": (
            "Command-text and file-diff audit; not a proof against deliberate obfuscation."
        ),
    }


def read_events(path: Path) -> list[dict[str, Any]]:
    events = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict):
            events.append(event)
    return events


def run_case(
    cli: str,
    config: dict[str, Any],
    row: dict[str, Any],
    directory: Path,
    runtime_python: Path | None = None,
) -> dict[str, Any]:
    directory.mkdir(parents=True, exist_ok=False)
    started = now()
    workspace, baseline, before = prepare_workspace(row, directory, runtime_python=runtime_python)
    command = cli_command(cli, workspace, config, directory / "agent-final.txt", runtime_python)
    python = str(runtime_python or Path(sys.executable).resolve())
    prompt = (
        config["prompts"][row["mode"]]
        + "\nRuntime: replace .venv/Scripts/python.exe with this project interpreter: "
        + python
        + "\nUse MCP evidence. Do not read dataset/runs.json or dataset/capabilities.json directly."
        + " Do not use git history to recover values or invoke a test suite."
        + " Read only this workspace, except the supplied Python interpreter and its packages."
    )
    (directory / "prompt.txt").write_bytes(prompt.encode("utf-8"))
    write_json(directory / "invocation.json", {"arguments": command, "started_at": started})
    timed_out = False
    preflight_ok = runtime_python is None or sandbox_preflight(
        cli,
        workspace,
        Path(python),
        directory,
    )
    with (
        (directory / "events.jsonl").open("wb") as out,
        (directory / "stderr.txt").open("wb") as err,
    ):
        try:
            if not preflight_ok:
                raise OSError("Sandbox runtime preflight failed; no model was invoked.")
            process = subprocess.Popen(
                command + [prompt],
                cwd=workspace,
                stdin=subprocess.DEVNULL,
                stdout=out,
                stderr=err,
            )
            try:
                returncode = process.wait(timeout=config["design"]["max_seconds_per_run"])
            except (subprocess.TimeoutExpired, KeyboardInterrupt):
                if sys.platform == "win32":
                    subprocess.run(
                        ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                        capture_output=True,
                        check=False,
                    )
                else:
                    process.kill()
                process.wait()
                returncode, timed_out = process.returncode, True
        except OSError as error:
            err.write(str(error).encode("utf-8"))
            returncode = -1
    events = read_events(directory / "events.jsonl")
    audit = audit_events(events, row["mode"])
    write_json(directory / "audit.json", audit)
    after = inventory(workspace)
    changed = sorted(
        name for name in before.keys() | after.keys() if before.get(name) != after.get(name)
    )
    catalog = workspace / "catalog/test_catalog.md"
    output = catalog.read_bytes() if catalog.is_file() else b""
    (directory / "agent-output.md").write_bytes(output)
    # The evaluator trusts original frozen inputs, not potentially edited copies.
    report = check_catalog(catalog, ROOT / "dataset", ROOT / "rules.yaml")
    write_json(directory / "final-checker.json", report.as_dict())
    protected = _protected_fields(baseline.decode("utf-8")) == _protected_fields(
        output.decode("utf-8", errors="replace")
    )
    scope = set(changed).issubset({"catalog/test_catalog.md"})
    stderr_text = (directory / "stderr.txt").read_text(encoding="utf-8", errors="replace")
    policy_blocked = "exec_command failed" in stderr_text and "blocked by policy" in stderr_text
    infrastructure_issues = list(audit["infrastructure_issues"])
    if not preflight_ok:
        infrastructure_issues.append("sandbox-runtime-preflight-failed")
    if policy_blocked:
        infrastructure_issues.append("command-execution-blocked-by-policy")
    if "sandbox failed" in stderr_text or "sandbox setup failed" in stderr_text:
        infrastructure_issues.append("sandbox-initialization-failed")
    interrupted = (
        timed_out or returncode != 0 or not audit["turn_completed"] or bool(infrastructure_issues)
    )
    success = report.valid and protected and scope and not audit["violations"] and not interrupted
    result = {
        **row,
        "started_at": started,
        "finished_at": now(),
        "status": "interrupted" if interrupted else "completed",
        "returncode": returncode,
        "timed_out": timed_out,
        "infrastructure_issues": infrastructure_issues,
        "success": success,
        "checker_valid": report.valid,
        "protected_fields_preserved": protected,
        "scope_preserved": scope,
        "changed_paths": changed,
        "checker_attempts": audit["checker_attempts"],
        "evidence_read": audit["evidence_read"],
        "violations": audit["violations"],
        "usage": audit["usage"],
        "baseline_sha256": sha256_bytes(baseline),
        "output_sha256": sha256_bytes(output),
    }
    write_json(directory / "result.json", result)
    return result


def wilson(successes: int, total: int) -> list[float] | None:
    if not total:
        return None
    z = 1.959963984540054
    proportion = successes / total
    denominator = 1 + z * z / total
    center = (proportion + z * z / (2 * total)) / denominator
    half = (
        z * math.sqrt(proportion * (1 - proportion) / total + z * z / (4 * total**2)) / denominator
    )
    return [max(0.0, center - half), min(1.0, center + half)]


def analyze(results: list[dict[str, Any]], expected: int) -> dict[str, Any]:
    completed = [result for result in results if result["status"] == "completed"]
    groups: dict[str, dict[str, Any]] = {}
    for condition in ("fault", "clean"):
        for mode in MODES:
            values = [r for r in completed if r["condition"] == condition and r["mode"] == mode]
            n = len(values)
            s = sum(r["success"] for r in values)
            groups[f"{condition}/{mode}"] = {
                "n": n,
                "successes": s,
                "rate": s / n if n else None,
                "wilson_95": wilson(s, n),
            }
    by_fault_class = {}
    for fault in FaultClass:
        for mode in MODES:
            values = [r for r in completed if r["fault_class"] == fault.value and r["mode"] == mode]
            n = len(values)
            s = sum(r["success"] for r in values)
            by_fault_class[f"{fault.value}/{mode}"] = {
                "n": n,
                "successes": s,
                "rate": s / n if n else None,
                "wilson_95": wilson(s, n),
            }
    pairs: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for result in completed:
        pairs[result["pair_id"]][result["mode"]] = result
    paired: dict[str, dict[str, Any]] = {}
    for condition in ("fault", "clean"):
        outcomes = {"both_success": 0, "with_only": 0, "without_only": 0, "both_failure": 0}
        for pair in pairs.values():
            if set(pair) != set(MODES) or pair[MODES[0]]["condition"] != condition:
                continue
            a, b = (pair[mode]["success"] for mode in MODES)
            key = (
                "both_success"
                if a and b
                else "with_only"
                if a
                else "without_only"
                if b
                else "both_failure"
            )
            outcomes[key] += 1
        discordant = outcomes["with_only"] + outcomes["without_only"]
        tail = min(outcomes["with_only"], outcomes["without_only"])
        p = min(1.0, 2 * sum(math.comb(discordant, k) for k in range(tail + 1)) / 2**discordant)
        total_pairs = sum(outcomes.values())
        paired[condition] = {
            **outcomes,
            "complete_pairs": total_pairs,
            "paired_rate_difference": (
                (outcomes["with_only"] - outcomes["without_only"]) / total_pairs
                if total_pairs
                else None
            ),
            "exact_p_two_sided": p if discordant else 1.0,
        }
    return {
        "expected_runs": expected,
        "completed_runs": len(completed),
        "interrupted_attempts": sum(r["status"] == "interrupted" for r in results),
        "complete": len(completed) == expected,
        "groups": groups,
        "by_fault_class": by_fault_class,
        "paired": paired,
        "interpretation": (
            "Exploratory paired case study; rates apply to this fixed dataset and configuration."
        ),
    }


def write_analysis(output: Path, plan: list[dict[str, Any]]) -> dict[str, Any]:
    attempts = [
        json.loads(p.read_text(encoding="utf-8"))
        for p in sorted((output / "runs").glob("*/*/result.json"))
    ]
    completed: dict[str, dict[str, Any]] = {}
    planned = {row["run_id"]: row for row in plan}
    for result in attempts:
        if result.get("run_id") not in planned or any(
            result.get(key) != value for key, value in planned[result["run_id"]].items()
        ):
            raise BatchError("Recorded result does not match the planned run matrix.")
        if result["status"] == "completed":
            if result["run_id"] in completed:
                raise BatchError(f"Duplicate completed run: {result['run_id']}")
            completed[result["run_id"]] = result
    summary = analyze(
        list(completed.values()) + [r for r in attempts if r["status"] == "interrupted"], len(plan)
    )
    write_json(output / "summary.json", summary)
    fields = [
        "run_id",
        "pair_id",
        "condition",
        "fault_class",
        "mode",
        "repetition",
        "success",
        "checker_attempts",
    ]
    with (output / "results.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(completed.values())
    lines = [
        "# Codex agent experiment results",
        "",
        f"Completed: {summary['completed_runs']}/{len(plan)}.",
        "",
        "| Condition / mode | Successful | Total | Rate | 95% Wilson interval |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for name, group in summary["groups"].items():
        rate = f"{group['rate']:.1%}" if group["rate"] is not None else "not measured"
        interval = group["wilson_95"]
        bounds = f"{interval[0]:.1%}–{interval[1]:.1%}" if interval else "not measured"
        lines.append(f"| {name} | {group['successes']} | {group['n']} | {rate} | {bounds} |")
    lines.extend(
        [
            "",
            "Paired outcomes and exact two-sided binomial tests are in summary.json.",
            "",
            "Fault repairs and clean controls are separate. Interrupted attempts are unscored.",
            "This is an exploratory case study on one dataset; "
            "intervals do not establish general model performance.",
        ]
    )
    (output / "report.md").write_bytes(("\n".join(lines) + "\n").encode("utf-8"))
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--pilot", action="store_true")
    action.add_argument("--run-all", action="store_true")
    action.add_argument("--summarize", action="store_true")
    parser.add_argument("--config", type=Path, default=ROOT / "eval/codex-protocol.yaml")
    parser.add_argument("--output", type=Path, default=ROOT / "eval/results/codex-eval-1")
    parser.add_argument("--codex", type=Path, help="Explicit path to the Codex CLI executable.")
    args = parser.parse_args()
    try:
        config = load_config(args.config)
        output = args.output.resolve()
        output.mkdir(parents=True, exist_ok=True)
        plan = make_plan(config)
        if args.summarize:
            print(json.dumps(write_analysis(output, plan), indent=2))
            return 0
        cli, version = find_codex(config["agent"]["version"], args.codex)
        if git("status", "--porcelain", "--untracked-files=all"):
            raise BatchError("Commit project changes before running measured experiments.")
        if not check_catalog(
            ROOT / "catalog/test_catalog.md", ROOT / "dataset", ROOT / "rules.yaml"
        ).valid:
            raise BatchError("Reference catalog must be valid before collection.")
        identity = {
            "config": config,
            "head": git("rev-parse", "HEAD"),
            "tracked_sha256": tracked_hashes(),
            "cli_version": version,
            "python": sys.version,
            "packages": {
                name: importlib.metadata.version(name) for name in ("mcp", "jsonschema", "PyYAML")
            },
            "plan": plan,
        }
        runtime_python = ensure_runtime(output)
        identity["runtime_python"] = str(runtime_python)
        runtime_marker = runtime_python.parent / "runtime-identity.json"
        if runtime_marker.is_file():
            identity["runtime_identity_sha256"] = sha256_bytes(runtime_marker.read_bytes())
        if args.pilot:
            rows = [row for row in plan if row["pair_id"] == "hallucinated-field-r03"]
            if len(rows) != 2:
                raise BatchError("Pilot pair is missing from plan.")
            pilot = output / "pilots" / datetime.now(UTC).strftime("%Y%m%dT%H%M%S%f")
            write_json(pilot / "identity.json", identity)
            write_json(
                output / "pilot-verification.json",
                {
                    "passed": False,
                    "identity": identity,
                    "pilot_path": str(pilot),
                    "status": "running",
                },
            )
            results = []
            for row in rows:
                result = run_case(
                    cli,
                    config,
                    row,
                    pilot / row["run_id"],
                    runtime_python=runtime_python,
                )
                results.append(result)
                print(
                    json.dumps(
                        {
                            "pilot": row["run_id"],
                            "status": result["status"],
                            "success": result["success"],
                        }
                    ),
                    flush=True,
                )
                if result["status"] == "interrupted":
                    raise BatchError(
                        f"Pilot interrupted. Inspect {pilot / row['run_id'] / 'stderr.txt'}"
                    )
            passed = all(r["evidence_read"] and not r["violations"] for r in results)
            write_json(
                output / "pilot-verification.json",
                {"passed": passed, "identity": identity, "pilot_path": str(pilot)},
            )
            if not passed:
                raise BatchError(
                    "Pilot found a procedure problem; inspect audit.json before freezing."
                )
            print("Pilot integration verified. Pilot results are excluded from final statistics.")
            return 0
        proof_path = output / "pilot-verification.json"
        if not proof_path.is_file():
            raise BatchError("Run --pilot successfully before final collection.")
        proof = json.loads(proof_path.read_text(encoding="utf-8"))
        if not proof["passed"] or proof["identity"] != identity:
            raise BatchError(
                "Pilot configuration changed or verification failed; repeat the pilot."
            )
        frozen_path = output / "frozen-protocol.json"
        if frozen_path.exists():
            frozen = json.loads(frozen_path.read_text(encoding="utf-8"))
            if frozen["identity"] != identity:
                raise BatchError(
                    "Current inputs differ from frozen protocol; refusing to mix results."
                )
        else:
            write_json(frozen_path, {"status": "frozen", "frozen_at": now(), "identity": identity})
        write_json(output / "plan.json", plan)
        for row in plan:
            if (
                tracked_hashes() != identity["tracked_sha256"]
                or git("rev-parse", "HEAD") != identity["head"]
            ):
                raise BatchError(
                    "Project changed during collection; refusing to mix configurations."
                )
            parent = output / "runs" / row["run_id"]
            previous = sorted(parent.glob("*/result.json"))
            if any(
                json.loads(p.read_text(encoding="utf-8"))["status"] == "completed" for p in previous
            ):
                continue
            if (
                previous
                and json.loads(previous[-1].read_text(encoding="utf-8"))["status"] == "interrupted"
            ):
                print(
                    f"Retrying previously interrupted {row['run_id']} in a new directory.",
                    flush=True,
                )
            attempt = parent / f"attempt-{len(list(parent.glob('attempt-*'))) + 1:02d}"
            result = run_case(cli, config, row, attempt, runtime_python=runtime_python)
            write_analysis(output, plan)
            print(
                json.dumps(
                    {"run": row["run_id"], "status": result["status"], "success": result["success"]}
                ),
                flush=True,
            )
            if result["status"] == "interrupted":
                raise BatchError(f"Infrastructure interruption. Inspect {attempt / 'stderr.txt'}")
        print(json.dumps(write_analysis(output, plan), indent=2))
        return 0
    except (BatchError, OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"Experiment stopped: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

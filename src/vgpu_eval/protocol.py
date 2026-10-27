"""Validation and execution helpers for the frozen agent experiment protocol."""

from __future__ import annotations

import csv
import json
import re
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker

from vgpu_catalog.hashing import sha256_bytes
from vgpu_catalog.rules import DEFAULT_RULES_PATH
from vgpu_eval.runs import start_agent_run, start_clean_agent_run

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROTOCOL_SCHEMA = PROJECT_ROOT / "schemas" / "evaluation-protocol.schema.json"
PLAN_FIELDS = [
    "order",
    "pair_id",
    "run_id",
    "condition",
    "fault_class",
    "testcase_id",
    "repetition",
    "mode",
    "prompt_path",
]
RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")


class ProtocolError(ValueError):
    """Raised when the frozen protocol or a planned run is inconsistent."""


def _inside_root(project_root: Path, relative_path: str) -> Path:
    root = project_root.resolve()
    candidate = (root / relative_path).resolve()
    if not candidate.is_relative_to(root):
        raise ProtocolError(f"Protocol path escapes the repository: {relative_path}")
    return candidate


def _load_protocol(protocol_path: Path) -> dict[str, Any]:
    value = yaml.safe_load(protocol_path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ProtocolError("Protocol must be a YAML object.")
    return value


def _load_plan(plan_path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with plan_path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        return list(reader.fieldnames or []), list(reader)


def _schema_issues(protocol: dict[str, Any], schema_path: Path) -> list[str]:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    issues: list[str] = []
    for error in sorted(validator.iter_errors(protocol), key=lambda item: list(item.path)):
        location = ".".join(str(part) for part in error.path) or "$"
        issues.append(f"schema:{location}: {error.message}")
    return issues


def _plan_issues(protocol: dict[str, Any], rows: list[dict[str, str]]) -> list[str]:
    issues: list[str] = []
    design = protocol["design"]
    modes = set(design["modes"])
    expected_rows = int(protocol["run_plan"]["expected_rows"])

    if len(rows) != expected_rows:
        issues.append(f"plan: expected {expected_rows} rows, found {len(rows)}")
    orders: list[int] = []
    run_ids: list[str] = []
    pairs: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row_index, row in enumerate(rows, start=2):
        try:
            orders.append(int(row["order"]))
            repetition = int(row["repetition"])
        except (TypeError, ValueError):
            issues.append(f"plan: row {row_index} has a non-integer order or repetition")
            continue
        run_id = row["run_id"]
        run_ids.append(run_id)
        if not RUN_ID_PATTERN.fullmatch(run_id):
            issues.append(f"plan: row {row_index} has invalid run_id {run_id!r}")
        if row["mode"] not in modes:
            issues.append(f"plan: row {row_index} has unknown mode {row['mode']!r}")
        expected_prompt = f"eval/prompts/{row['mode']}.md"
        if row["prompt_path"] != expected_prompt:
            issues.append(f"plan: row {row_index} must use {expected_prompt}")
        if repetition < 1:
            issues.append(f"plan: row {row_index} has repetition below one")
        pairs[row["pair_id"]].append(row)

    if orders != list(range(1, len(rows) + 1)):
        issues.append("plan: order values must be consecutive and match CSV row order")
    if len(run_ids) != len(set(run_ids)):
        issues.append("plan: run_id values must be unique")

    fault_targets = {
        item["fault_class"]: item["testcase_id"] for item in design["fault_cases"]
    }
    expected_fault_pairs = {
        (fault, testcase, repetition)
        for fault, testcase in fault_targets.items()
        for repetition in range(1, int(design["repetitions_per_fault"]) + 1)
    }
    expected_clean_repetitions = set(range(1, int(design["clean_control_pairs"]) + 1))
    actual_fault_pairs: set[tuple[str, str, int]] = set()
    actual_clean_repetitions: set[int] = set()

    for pair_id, pair_rows in pairs.items():
        pair_modes = {row["mode"] for row in pair_rows}
        if len(pair_rows) != len(modes) or pair_modes != modes:
            issues.append(f"plan: pair {pair_id!r} must contain each mode exactly once")
            continue
        invariant_fields = {"condition", "fault_class", "testcase_id", "repetition"}
        if any(len({row[field] for row in pair_rows}) != 1 for field in invariant_fields):
            issues.append(f"plan: pair {pair_id!r} does not hold paired inputs constant")
            continue
        first = pair_rows[0]
        repetition = int(first["repetition"])
        if first["condition"] == "fault":
            fault = first["fault_class"]
            testcase = first["testcase_id"]
            if fault_targets.get(fault) != testcase:
                issues.append(f"plan: pair {pair_id!r} uses an undeclared fault target")
            actual_fault_pairs.add((fault, testcase, repetition))
        elif first["condition"] == "clean":
            if first["fault_class"] or first["testcase_id"]:
                issues.append(f"plan: clean pair {pair_id!r} must not name a fault or test case")
            actual_clean_repetitions.add(repetition)
        else:
            issues.append(f"plan: pair {pair_id!r} has unknown condition")

    if actual_fault_pairs != expected_fault_pairs:
        issues.append("plan: fault pairs do not match the frozen fault/repetition matrix")
    if actual_clean_repetitions != expected_clean_repetitions:
        issues.append("plan: clean pairs do not match the frozen repetition matrix")
    if len(actual_fault_pairs) != int(design["fault_pairs"]):
        issues.append("plan: fault pair count differs from design.fault_pairs")
    if len(pairs) != int(design["total_pairs"]):
        issues.append("plan: total pair count differs from design.total_pairs")
    if len(rows) != int(design["total_runs"]):
        issues.append("plan: run count differs from design.total_runs")
    return issues


def verify_protocol(
    protocol_path: Path,
    *,
    project_root: Path = PROJECT_ROOT,
    schema_path: Path = PROTOCOL_SCHEMA,
) -> dict[str, Any]:
    """Validate schema, frozen input hashes, and the complete paired run plan."""

    protocol_path = protocol_path.resolve()
    project_root = project_root.resolve()
    issues: list[str] = []
    try:
        protocol = _load_protocol(protocol_path)
        issues.extend(_schema_issues(protocol, schema_path.resolve()))
    except (OSError, ProtocolError, yaml.YAMLError, json.JSONDecodeError) as error:
        return {
            "valid": False,
            "protocol_path": str(protocol_path),
            "issues": [str(error)],
        }

    protocol_id = str(protocol.get("protocol_id", ""))
    plan_path: Path | None = None
    rows: list[dict[str, str]] = []
    if not issues:
        for item in protocol["inputs"]["files"]:
            try:
                input_path = _inside_root(project_root, item["path"])
                actual_hash = sha256_bytes(input_path.read_bytes())
                if actual_hash != item["sha256"]:
                    issues.append(f"input:{item['path']}: SHA-256 mismatch")
            except (OSError, ProtocolError) as error:
                issues.append(f"input:{item['path']}: {error}")

        try:
            plan_path = _inside_root(project_root, protocol["run_plan"]["path"])
            plan_bytes = plan_path.read_bytes()
            if sha256_bytes(plan_bytes) != protocol["run_plan"]["sha256"]:
                issues.append("plan: SHA-256 mismatch")
            fields, rows = _load_plan(plan_path)
            if fields != PLAN_FIELDS:
                issues.append(f"plan: CSV columns must be {', '.join(PLAN_FIELDS)}")
            else:
                issues.extend(_plan_issues(protocol, rows))
        except (OSError, ProtocolError) as error:
            issues.append(f"plan: {error}")

    fault_pair_count = len(
        {row.get("pair_id") for row in rows if row.get("condition") == "fault"}
    )
    clean_pair_count = len(
        {row.get("pair_id") for row in rows if row.get("condition") == "clean"}
    )
    return {
        "valid": not issues,
        "protocol_id": protocol_id,
        "protocol_path": str(protocol_path),
        "protocol_sha256": sha256_bytes(protocol_path.read_bytes()),
        "plan_path": str(plan_path) if plan_path else None,
        "plan_sha256": (
            sha256_bytes(plan_path.read_bytes()) if plan_path and plan_path.is_file() else None
        ),
        "runs": len(rows),
        "fault_pairs": fault_pair_count,
        "clean_pairs": clean_pair_count,
        "issues": issues,
    }


def _git(project_root: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(project_root), *arguments],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise ProtocolError(f"git {' '.join(arguments)} failed: {detail}")
    return completed.stdout.strip()


def start_planned_run(
    protocol_path: Path,
    run_id: str,
    catalog_path: Path,
    dataset_dir: Path,
    results_dir: Path,
    *,
    rules_path: Path = DEFAULT_RULES_PATH,
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    """Start exactly one frozen-plan run after enforcing repository preconditions."""

    report = verify_protocol(protocol_path, project_root=project_root)
    if not report["valid"]:
        raise ProtocolError("Protocol verification failed: " + "; ".join(report["issues"]))
    protocol = _load_protocol(protocol_path.resolve())
    plan_path = _inside_root(project_root, protocol["run_plan"]["path"])
    _, rows = _load_plan(plan_path)
    matches = [row for row in rows if row["run_id"] == run_id]
    if len(matches) != 1:
        raise ProtocolError(f"Expected one planned row for {run_id!r}; found {len(matches)}.")
    row = matches[0]

    head = _git(project_root, "rev-parse", "HEAD")
    tag_head = _git(project_root, "rev-list", "-n", "1", protocol["repository"]["freeze_tag"])
    if head != tag_head:
        raise ProtocolError(
            f"HEAD must equal frozen tag {protocol['repository']['freeze_tag']} ({tag_head})."
        )
    worktree = _git(project_root, "status", "--porcelain", "--untracked-files=all")
    if worktree:
        raise ProtocolError("Worktree must be clean before a planned run.")

    protocol_metadata = {
        "protocol_id": protocol["protocol_id"],
        "protocol_sha256": report["protocol_sha256"],
        "plan_sha256": report["plan_sha256"],
        "plan_order": int(row["order"]),
        "pair_id": row["pair_id"],
        "repetition": int(row["repetition"]),
        "condition": row["condition"],
        "cursor_version": protocol["environment"]["cursor"]["version"],
        "reasoning_mode": protocol["environment"]["cursor"]["reasoning_mode"],
        "repository_root": str(project_root.resolve()),
        "repository_head": head,
        "allowed_modified_path": protocol["success_criteria"]["allowed_modified_path"],
    }
    common = {
        "catalog_path": catalog_path,
        "dataset_dir": dataset_dir,
        "results_dir": results_dir,
        "model_id": protocol["environment"]["cursor"]["model"],
        "mode": row["mode"],
        "run_id": row["run_id"],
        "rules_path": rules_path,
        "prompt_path": _inside_root(project_root, row["prompt_path"]),
        "protocol_metadata": protocol_metadata,
    }
    if row["condition"] == "clean":
        return start_clean_agent_run(**common)
    return start_agent_run(
        **common,
        fault_class=row["fault_class"],
        testcase_id=row["testcase_id"],
    )

"""Lifecycle and aggregation for interactive Cursor agent experiments."""

from __future__ import annotations

import json
import re
import subprocess
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from catalog_check.checker import check_catalog
from vgpu_catalog.hashing import pretty_json_bytes, sha256_bytes
from vgpu_catalog.rules import DEFAULT_RULES_PATH
from vgpu_eval.faults import FaultClass, inject_fault

RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")
SECTION_PATTERN = re.compile(r"^## (?P<testcase_id>TC-[0-9]{3})\s*$", re.MULTILINE)
FIELD_PATTERN = re.compile(r"^### (?P<name>[^\r\n]+?)\s*$", re.MULTILINE)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROMPT_DIR = PROJECT_ROOT / "eval" / "prompts"


class AgentRunError(ValueError):
    """Raised when an interactive experiment would be ambiguous or destructive."""


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def default_run_id(fault_class: FaultClass | str, testcase_id: str) -> str:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"{stamp}-{FaultClass(fault_class).value}-{testcase_id.lower()}"


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_bytes(pretty_json_bytes(value))


def _input_identity(dataset_dir: Path, rules_path: Path) -> dict[str, str]:
    manifest = json.loads((dataset_dir / "manifest.json").read_text(encoding="utf-8"))
    return {
        "dataset_id": str(manifest["dataset_id"]),
        "source_hash": str(manifest["snapshot_hash"]),
        "rules_sha256": sha256_bytes(rules_path.read_bytes()),
    }


def _load_run(run_dir: Path) -> dict[str, Any]:
    manifest_path = run_dir / "run.json"
    if not manifest_path.is_file():
        raise AgentRunError(f"Run manifest does not exist: {manifest_path}")
    value = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AgentRunError("Run manifest must be a JSON object.")
    return value


def _protected_fields(document: str) -> dict[str, dict[str, str]]:
    sections = list(SECTION_PATTERN.finditer(document))
    protected: dict[str, dict[str, str]] = {}
    for index, section in enumerate(sections):
        section_end = sections[index + 1].start() if index + 1 < len(sections) else len(document)
        section_text = document[section.start() : section_end]
        fields = list(FIELD_PATTERN.finditer(section_text))
        values: dict[str, str] = {}
        for field_index, field in enumerate(fields):
            if field.group("name") not in {"Purpose", "Notes"}:
                continue
            field_end = fields[field_index + 1].start() if field_index + 1 < len(fields) else len(
                section_text
            )
            values[field.group("name")] = section_text[field.end() : field_end]
        protected[section.group("testcase_id")] = values
    return protected


def _open_runs(results_dir: Path) -> list[str]:
    if not results_dir.is_dir():
        return []
    open_runs: list[str] = []
    for manifest_path in sorted(results_dir.glob("*/run.json")):
        try:
            value = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if value.get("status") in {"awaiting-agent", "recorded"}:
            open_runs.append(str(value.get("run_id", manifest_path.parent.name)))
    return open_runs


def _git_modified_paths(repository_root: Path, repository_head: str) -> list[str]:
    completed = subprocess.run(
        ["git", "-C", str(repository_root), "diff", "--name-only", repository_head, "--"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise AgentRunError(f"Could not inspect experiment worktree: {detail}")
    return sorted(path for path in completed.stdout.splitlines() if path)


def start_agent_run(
    catalog_path: Path,
    dataset_dir: Path,
    results_dir: Path,
    *,
    fault_class: FaultClass | str,
    testcase_id: str,
    model_id: str,
    mode: str,
    run_id: str | None = None,
    rules_path: Path = DEFAULT_RULES_PATH,
    prompt_path: Path | None = None,
    protocol_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Save a valid baseline, inject one fault in place, and open an agent run."""

    if mode not in {"with-checker", "without-checker"}:
        raise AgentRunError("mode must be 'with-checker' or 'without-checker'.")
    if not model_id.strip():
        raise AgentRunError("model_id must not be empty.")

    catalog_path = catalog_path.resolve()
    dataset_dir = dataset_dir.resolve()
    results_dir = results_dir.resolve()
    rules_path = rules_path.resolve()
    prompt_path = (prompt_path or PROMPT_DIR / f"{mode}.md").resolve()
    prompt_bytes = prompt_path.read_bytes()
    if not prompt_bytes.strip():
        raise AgentRunError("Experiment prompt must not be empty.")
    open_runs = _open_runs(results_dir)
    if open_runs:
        raise AgentRunError(f"Finish and restore the open run first: {', '.join(open_runs)}")

    identifier = run_id or default_run_id(fault_class, testcase_id)
    if not RUN_ID_PATTERN.fullmatch(identifier):
        raise AgentRunError(
            "run_id may contain only letters, numbers, dot, underscore, and hyphen."
        )
    run_dir = results_dir / identifier
    if run_dir.exists():
        raise AgentRunError(f"Run directory already exists: {run_dir}")

    baseline_bytes = catalog_path.read_bytes()
    baseline = baseline_bytes.decode("utf-8")
    baseline_report = check_catalog(catalog_path, dataset_dir, rules_path)
    if not baseline_report.valid:
        raise AgentRunError("Catalog must pass before an interactive fault is injected.")
    input_identity = _input_identity(dataset_dir, rules_path)

    faulty, injection = inject_fault(baseline, fault_class, testcase_id, rules_path)
    faulty_bytes = faulty.encode("utf-8")
    temporary_catalog = catalog_path.with_name(f".{catalog_path.name}.eval.tmp")
    temporary_catalog.write_bytes(faulty_bytes)
    faulty_report = check_catalog(temporary_catalog, dataset_dir, rules_path)
    if faulty_report.valid:
        temporary_catalog.unlink(missing_ok=True)
        raise AgentRunError("Injected fault was not detected; refusing to start the run.")

    run_dir.mkdir(parents=True)
    (run_dir / "baseline-catalog.md").write_bytes(baseline_bytes)
    (run_dir / "faulty-catalog.md").write_bytes(faulty_bytes)
    (run_dir / "prompt.md").write_bytes(prompt_bytes)
    _write_json(
        run_dir / "initial-checker-report.json",
        {"mode": "check", **faulty_report.as_dict()},
    )
    manifest = {
        "schema_version": "1.0",
        "run_id": identifier,
        "status": "awaiting-agent",
        "started_at": _now(),
        "model_id": model_id.strip(),
        "mode": mode,
        "prompt_id": prompt_path.stem,
        "prompt_sha256": sha256_bytes(prompt_bytes),
        "catalog_path": str(catalog_path),
        "dataset_dir": str(dataset_dir),
        "rules_path": str(rules_path),
        **input_identity,
        "fault": injection.as_dict(),
        "baseline_catalog_sha256": sha256_bytes(baseline_bytes),
        "faulty_catalog_sha256": sha256_bytes(faulty_bytes),
        "initial_issue_codes": sorted({issue.code for issue in faulty_report.issues}),
    }
    if protocol_metadata is not None:
        manifest["protocol"] = protocol_metadata
    _write_json(run_dir / "run.json", manifest)
    temporary_catalog.replace(catalog_path)
    return manifest


def start_clean_agent_run(
    catalog_path: Path,
    dataset_dir: Path,
    results_dir: Path,
    *,
    model_id: str,
    mode: str,
    run_id: str,
    rules_path: Path = DEFAULT_RULES_PATH,
    prompt_path: Path | None = None,
    protocol_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Open a clean-control run without mutating the valid catalog."""

    if mode not in {"with-checker", "without-checker"}:
        raise AgentRunError("mode must be 'with-checker' or 'without-checker'.")
    if not model_id.strip():
        raise AgentRunError("model_id must not be empty.")
    if not RUN_ID_PATTERN.fullmatch(run_id):
        raise AgentRunError(
            "run_id may contain only letters, numbers, dot, underscore, and hyphen."
        )

    catalog_path = catalog_path.resolve()
    dataset_dir = dataset_dir.resolve()
    results_dir = results_dir.resolve()
    rules_path = rules_path.resolve()
    prompt_path = (prompt_path or PROMPT_DIR / f"{mode}.md").resolve()
    prompt_bytes = prompt_path.read_bytes()
    if not prompt_bytes.strip():
        raise AgentRunError("Experiment prompt must not be empty.")
    open_runs = _open_runs(results_dir)
    if open_runs:
        raise AgentRunError(f"Finish and restore the open run first: {', '.join(open_runs)}")

    run_dir = results_dir / run_id
    if run_dir.exists():
        raise AgentRunError(f"Run directory already exists: {run_dir}")
    baseline_bytes = catalog_path.read_bytes()
    baseline_report = check_catalog(catalog_path, dataset_dir, rules_path)
    if not baseline_report.valid:
        raise AgentRunError("Catalog must pass before a clean-control run is started.")

    run_dir.mkdir(parents=True)
    (run_dir / "baseline-catalog.md").write_bytes(baseline_bytes)
    (run_dir / "input-catalog.md").write_bytes(baseline_bytes)
    (run_dir / "prompt.md").write_bytes(prompt_bytes)
    _write_json(
        run_dir / "initial-checker-report.json",
        {"mode": "check", **baseline_report.as_dict()},
    )
    manifest = {
        "schema_version": "1.0",
        "run_id": run_id,
        "status": "awaiting-agent",
        "started_at": _now(),
        "model_id": model_id.strip(),
        "mode": mode,
        "prompt_id": prompt_path.stem,
        "prompt_sha256": sha256_bytes(prompt_bytes),
        "catalog_path": str(catalog_path),
        "dataset_dir": str(dataset_dir),
        "rules_path": str(rules_path),
        **_input_identity(dataset_dir, rules_path),
        "fault": {
            "fault_class": "clean-control",
            "testcase_id": None,
            "changed_path": None,
            "original": None,
            "injected": None,
            "expected_issue_codes": [],
        },
        "baseline_catalog_sha256": sha256_bytes(baseline_bytes),
        "input_catalog_sha256": sha256_bytes(baseline_bytes),
        "initial_issue_codes": [],
    }
    if protocol_metadata is not None:
        manifest["protocol"] = protocol_metadata
    _write_json(run_dir / "run.json", manifest)
    return manifest


def finish_agent_run(
    catalog_path: Path,
    dataset_dir: Path,
    results_dir: Path,
    *,
    run_id: str,
    checker_attempts: int,
    notes: str | None = None,
    rules_path: Path = DEFAULT_RULES_PATH,
) -> dict[str, Any]:
    """Record agent output and objective outcome without restoring the catalog."""

    if not 0 <= checker_attempts <= 3:
        raise AgentRunError("checker_attempts must be between 0 and 3.")

    catalog_path = catalog_path.resolve()
    dataset_dir = dataset_dir.resolve()
    results_dir = results_dir.resolve()
    rules_path = rules_path.resolve()
    run_dir = results_dir / run_id
    manifest = _load_run(run_dir)
    if manifest.get("status") != "awaiting-agent":
        raise AgentRunError(f"Run status must be awaiting-agent, not {manifest.get('status')!r}.")
    expected_paths = {
        "catalog_path": str(catalog_path),
        "dataset_dir": str(dataset_dir),
        "rules_path": str(rules_path),
    }
    for name, expected in expected_paths.items():
        if manifest.get(name) != expected:
            raise AgentRunError(f"{name} differs from the path recorded at run start.")
    for name, expected in _input_identity(dataset_dir, rules_path).items():
        if manifest.get(name) != expected:
            raise AgentRunError(f"{name} changed after run start; refusing to score the run.")
    if manifest.get("mode") == "with-checker" and checker_attempts < 1:
        raise AgentRunError("with-checker runs require at least one checker attempt.")

    baseline_bytes = (run_dir / "baseline-catalog.md").read_bytes()
    agent_bytes = catalog_path.read_bytes()
    (run_dir / "agent-output.md").write_bytes(agent_bytes)
    report = check_catalog(catalog_path, dataset_dir, rules_path)
    _write_json(run_dir / "final-checker-report.json", {"mode": "check", **report.as_dict()})

    baseline_protected = _protected_fields(baseline_bytes.decode("utf-8"))
    agent_protected = _protected_fields(agent_bytes.decode("utf-8"))
    protected_preserved = baseline_protected == agent_protected
    checker_valid = report.valid
    protocol = manifest.get("protocol")
    repository_scope_preserved = True
    modified_paths: list[str] = []
    if isinstance(protocol, dict):
        repository_root = Path(str(protocol["repository_root"]))
        repository_head = str(protocol["repository_head"])
        modified_paths = _git_modified_paths(repository_root, repository_head)
        repository_scope_preserved = set(modified_paths).issubset(
            {str(protocol["allowed_modified_path"])}
        )
    success = checker_valid and protected_preserved and repository_scope_preserved
    manifest["status"] = "recorded"
    manifest["finished_at"] = _now()
    manifest["agent_output_sha256"] = sha256_bytes(agent_bytes)
    manifest["result"] = {
        "success": success,
        "checker_valid": checker_valid,
        "protected_fields_preserved": protected_preserved,
        "checker_attempts": checker_attempts,
        "escalated": not success,
        "remaining_issue_codes": sorted({issue.code for issue in report.issues}),
        "remaining_issue_paths": sorted({issue.path for issue in report.issues}),
    }
    if isinstance(protocol, dict):
        manifest["result"]["repository_scope_preserved"] = repository_scope_preserved
        manifest["result"]["modified_paths"] = modified_paths
    if notes:
        manifest["notes"] = notes
    _write_json(run_dir / "run.json", manifest)
    return manifest


def restore_agent_run(catalog_path: Path, results_dir: Path, *, run_id: str) -> dict[str, Any]:
    """Restore a recorded baseline, refusing to overwrite later unrecorded edits."""

    catalog_path = catalog_path.resolve()
    results_dir = results_dir.resolve()
    run_dir = results_dir / run_id
    manifest = _load_run(run_dir)
    if manifest.get("status") == "restored":
        return manifest
    if manifest.get("status") != "recorded":
        raise AgentRunError("Finish the run before restoring its baseline.")
    if manifest.get("catalog_path") != str(catalog_path):
        raise AgentRunError("catalog_path differs from the path recorded at run start.")

    current_bytes = catalog_path.read_bytes()
    if sha256_bytes(current_bytes) != manifest.get("agent_output_sha256"):
        raise AgentRunError("Catalog changed after finish; refusing to overwrite unrecorded edits.")
    baseline_bytes = (run_dir / "baseline-catalog.md").read_bytes()
    if sha256_bytes(baseline_bytes) != manifest.get("baseline_catalog_sha256"):
        raise AgentRunError("Recorded baseline hash does not match the run manifest.")
    temporary = catalog_path.with_name(f".{catalog_path.name}.restore.tmp")
    temporary.write_bytes(baseline_bytes)
    temporary.replace(catalog_path)
    manifest["status"] = "restored"
    manifest["restored_at"] = _now()
    _write_json(run_dir / "run.json", manifest)
    return manifest


def _group_metrics(runs: list[dict[str, Any]]) -> dict[str, int | float]:
    total = len(runs)
    successes = sum(bool(run["result"]["success"]) for run in runs)
    checker_valid = sum(bool(run["result"]["checker_valid"]) for run in runs)
    protected = sum(bool(run["result"]["protected_fields_preserved"]) for run in runs)
    attempts = [int(run["result"]["checker_attempts"]) for run in runs]
    return {
        "runs": total,
        "successful_runs": successes,
        "repair_success_rate": successes / total if total else 0.0,
        "checker_valid_rate": checker_valid / total if total else 0.0,
        "guardrail_compliance_rate": protected / total if total else 0.0,
        "escalation_rate": (total - successes) / total if total else 0.0,
        "mean_checker_attempts": sum(attempts) / total if total else 0.0,
    }


def summarize_agent_runs(results_dir: Path) -> dict[str, Any]:
    """Aggregate all recorded/restored runs by fault, mode, and model."""

    results_dir = results_dir.resolve()
    runs: list[dict[str, Any]] = []
    for path in sorted(results_dir.glob("*/run.json")) if results_dir.is_dir() else []:
        value = json.loads(path.read_text(encoding="utf-8"))
        if value.get("status") in {"recorded", "restored"} and "result" in value:
            runs.append(value)

    grouped: dict[str, dict[str, list[dict[str, Any]]]] = {
        "by_fault_class": defaultdict(list),
        "by_mode": defaultdict(list),
        "by_model": defaultdict(list),
    }
    for run in runs:
        grouped["by_fault_class"][run["fault"]["fault_class"]].append(run)
        grouped["by_mode"][run["mode"]].append(run)
        grouped["by_model"][run["model_id"]].append(run)

    return {
        "schema_version": "1.0",
        "metrics": _group_metrics(runs),
        "by_fault_class": {
            key: _group_metrics(values)
            for key, values in sorted(grouped["by_fault_class"].items())
        },
        "by_mode": {
            key: _group_metrics(values) for key, values in sorted(grouped["by_mode"].items())
        },
        "by_model": {
            key: _group_metrics(values) for key, values in sorted(grouped["by_model"].items())
        },
        "run_ids": [run["run_id"] for run in runs],
    }

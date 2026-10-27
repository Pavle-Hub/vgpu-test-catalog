import json
from pathlib import Path
from shutil import copyfile

import pytest

from catalog_check.checker import check_catalog
from catalog_check.markdown import find_blocks
from vgpu_eval.faults import FaultClass, inject_fault
from vgpu_eval.protocol import verify_protocol
from vgpu_eval.runs import (
    AgentRunError,
    finish_agent_run,
    restore_agent_run,
    start_agent_run,
    start_clean_agent_run,
    summarize_agent_runs,
)
from vgpu_eval.suite import generate_detection_suite

REFERENCE_CATALOG = Path("catalog/test_catalog.md")
DATASET_DIR = Path("dataset")
PROTOCOL_PATH = Path("eval/protocol-v2.yaml")


def _without_target_block(document: str, testcase_id: str) -> str:
    block = next(item for item in find_blocks(document) if item.testcase_id == testcase_id)
    return document[: block.start] + "<TARGET-DERIVED-BLOCK>" + document[block.end :]


@pytest.mark.parametrize("fault_class", list(FaultClass))
def test_each_fault_is_deterministic_scoped_and_detected(
    tmp_path: Path,
    fault_class: FaultClass,
) -> None:
    baseline = REFERENCE_CATALOG.read_bytes().decode("utf-8")

    first, metadata = inject_fault(baseline, fault_class, "TC-001")
    second, repeated_metadata = inject_fault(baseline, fault_class, "TC-001")
    faulty_path = tmp_path / f"{fault_class.value}.md"
    faulty_path.write_bytes(first.encode("utf-8"))
    report = check_catalog(faulty_path, DATASET_DIR)

    assert first == second
    assert metadata == repeated_metadata
    assert _without_target_block(first, "TC-001") == _without_target_block(
        baseline, "TC-001"
    )
    assert not report.valid
    issue_codes = {issue.code for issue in report.issues}
    assert set(metadata.expected_issue_codes).issubset(issue_codes)


def test_detection_suite_includes_faults_and_clean_control(tmp_path: Path) -> None:
    output_dir = tmp_path / "suite"

    suite = generate_detection_suite(
        REFERENCE_CATALOG,
        DATASET_DIR,
        output_dir,
        selected_testcases=["TC-001"],
    )

    assert len(suite["cases"]) == 6
    assert suite["dataset_id"] == "dataset-reference-2026"
    assert suite["source_hash"] == (
        "83c9a22581b017a0ebc967d7c5bd4ef53f6c9edcb246e696ab402314a5eef394"
    )
    assert len(suite["rules_sha256"]) == 64
    assert suite["metrics"] == {
        "true_positive": 5,
        "false_negative": 0,
        "false_positive": 0,
        "true_negative": 1,
        "precision": 1.0,
        "recall": 1.0,
        "detection_rate": 1.0,
        "false_pass_rate": 0.0,
        "false_fail_rate": 0.0,
        "accuracy": 1.0,
    }
    persisted = json.loads((output_dir / "suite.json").read_text(encoding="utf-8"))
    assert persisted == suite


def test_frozen_protocol_inputs_and_plan_are_valid() -> None:
    report = verify_protocol(PROTOCOL_PATH)

    assert report["valid"], report["issues"]
    assert report["runs"] == 60
    assert report["fault_pairs"] == 25
    assert report["clean_pairs"] == 5


def test_superseded_protocol_remains_auditable() -> None:
    report = verify_protocol(Path("eval/protocol-v1.yaml"))

    assert report["valid"], report["issues"]
    assert report["protocol_id"] == "vgpu-agent-eval-v1"


def test_agent_run_can_be_started_recorded_summarized_and_restored(tmp_path: Path) -> None:
    catalog_path = tmp_path / "test_catalog.md"
    copyfile(REFERENCE_CATALOG, catalog_path)
    results_dir = tmp_path / "runs"

    started = start_agent_run(
        catalog_path,
        DATASET_DIR,
        results_dir,
        fault_class=FaultClass.FALSE_PROVENANCE,
        testcase_id="TC-001",
        model_id="Cursor Grok 4.6",
        mode="with-checker",
        run_id="test-run",
    )
    assert started["status"] == "awaiting-agent"
    assert started["dataset_id"] == "dataset-reference-2026"
    assert len(started["rules_sha256"]) == 64
    assert started["prompt_id"] == "with-checker"
    assert len(started["prompt_sha256"]) == 64
    assert (results_dir / "test-run" / "prompt.md").read_text(encoding="utf-8") == (
        "/sync-catalog\n"
    )
    assert not check_catalog(catalog_path, DATASET_DIR).valid

    copyfile(results_dir / "test-run" / "baseline-catalog.md", catalog_path)
    finished = finish_agent_run(
        catalog_path,
        DATASET_DIR,
        results_dir,
        run_id="test-run",
        checker_attempts=2,
    )
    assert finished["status"] == "recorded"
    assert finished["result"] == {
        "success": True,
        "checker_valid": True,
        "protected_fields_preserved": True,
        "checker_attempts": 2,
        "escalated": False,
        "remaining_issue_codes": [],
        "remaining_issue_paths": [],
    }

    manifest_path = results_dir / "test-run" / "run.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["protocol"] = {"protocol_id": "test-protocol"}
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    summary = summarize_agent_runs(results_dir, protocol_id="test-protocol")
    assert summary["metrics"]["repair_success_rate"] == 1.0
    assert summary["by_fault_class"]["false-provenance"]["runs"] == 1
    excluded = summarize_agent_runs(results_dir, excluded_run_ids={"test-run"})
    assert excluded["metrics"]["runs"] == 0

    restored = restore_agent_run(catalog_path, results_dir, run_id="test-run")
    assert restored["status"] == "restored"
    assert catalog_path.read_bytes() == REFERENCE_CATALOG.read_bytes()


def test_clean_control_run_can_be_recorded_and_restored(tmp_path: Path) -> None:
    catalog_path = tmp_path / "test_catalog.md"
    copyfile(REFERENCE_CATALOG, catalog_path)
    results_dir = tmp_path / "runs"

    started = start_clean_agent_run(
        catalog_path,
        DATASET_DIR,
        results_dir,
        model_id="Cursor Grok 4.6",
        mode="without-checker",
        run_id="clean-control",
    )
    assert started["fault"]["fault_class"] == "clean-control"
    assert started["initial_issue_codes"] == []

    finished = finish_agent_run(
        catalog_path,
        DATASET_DIR,
        results_dir,
        run_id="clean-control",
        checker_attempts=0,
    )
    assert finished["result"]["success"]

    summary = summarize_agent_runs(results_dir)
    assert summary["by_fault_class"]["clean-control"]["runs"] == 1
    restored = restore_agent_run(catalog_path, results_dir, run_id="clean-control")
    assert restored["status"] == "restored"


def test_restore_refuses_to_discard_unrecorded_agent_work(tmp_path: Path) -> None:
    catalog_path = tmp_path / "test_catalog.md"
    copyfile(REFERENCE_CATALOG, catalog_path)
    results_dir = tmp_path / "runs"
    start_agent_run(
        catalog_path,
        DATASET_DIR,
        results_dir,
        fault_class=FaultClass.WRONG_VALUE,
        testcase_id="TC-001",
        model_id="Cursor Grok 4.6",
        mode="with-checker",
        run_id="active-run",
    )

    with pytest.raises(AgentRunError, match="Finish the run"):
        restore_agent_run(catalog_path, results_dir, run_id="active-run")

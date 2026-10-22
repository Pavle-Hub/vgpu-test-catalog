"""Generate a deterministic checker-detection suite with clean controls."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from catalog_check.checker import CatalogReport, check_catalog
from vgpu_catalog.hashing import pretty_json_bytes, sha256_bytes
from vgpu_catalog.rules import DEFAULT_RULES_PATH
from vgpu_eval.faults import FaultClass, inject_fault, testcase_ids


class EvaluationSuiteError(ValueError):
    """Raised when a checker suite cannot be generated safely."""


def _report_value(report: CatalogReport) -> dict[str, Any]:
    return {"mode": "check", **report.as_dict()}


def confusion_metrics(cases: list[dict[str, Any]]) -> dict[str, int | float]:
    """Return confusion-matrix metrics where invalid means fault detected."""

    true_positive = sum(case["expected_invalid"] and not case["checker_valid"] for case in cases)
    false_negative = sum(case["expected_invalid"] and case["checker_valid"] for case in cases)
    false_positive = sum(
        not case["expected_invalid"] and not case["checker_valid"] for case in cases
    )
    true_negative = sum(
        not case["expected_invalid"] and case["checker_valid"] for case in cases
    )
    predicted_positive = true_positive + false_positive
    actual_positive = true_positive + false_negative
    total = len(cases)
    return {
        "true_positive": true_positive,
        "false_negative": false_negative,
        "false_positive": false_positive,
        "true_negative": true_negative,
        "precision": true_positive / predicted_positive if predicted_positive else 0.0,
        "recall": true_positive / actual_positive if actual_positive else 0.0,
        "detection_rate": true_positive / actual_positive if actual_positive else 0.0,
        "false_pass_rate": false_negative / actual_positive if actual_positive else 0.0,
        "false_fail_rate": false_positive / (false_positive + true_negative)
        if false_positive + true_negative
        else 0.0,
        "accuracy": (true_positive + true_negative) / total if total else 0.0,
    }


def _write_case(
    output_dir: Path,
    case_id: str,
    catalog_bytes: bytes,
    dataset_dir: Path,
    rules_path: Path,
) -> CatalogReport:
    case_dir = output_dir / "cases" / case_id
    case_dir.mkdir(parents=True)
    catalog_path = case_dir / "catalog.md"
    catalog_path.write_bytes(catalog_bytes)
    report = check_catalog(catalog_path, dataset_dir, rules_path)
    (case_dir / "checker-report.json").write_bytes(pretty_json_bytes(_report_value(report)))
    return report


def generate_detection_suite(
    reference_catalog: Path,
    dataset_dir: Path,
    output_dir: Path,
    *,
    rules_path: Path = DEFAULT_RULES_PATH,
    selected_testcases: list[str] | None = None,
) -> dict[str, Any]:
    """Generate clean and faulty cases, run the checker, and calculate metrics."""

    reference_catalog = reference_catalog.resolve()
    dataset_dir = dataset_dir.resolve()
    rules_path = rules_path.resolve()
    output_dir = output_dir.resolve()
    if output_dir.exists() and any(output_dir.iterdir()):
        raise EvaluationSuiteError(f"Output directory is not empty: {output_dir}")

    baseline_bytes = reference_catalog.read_bytes()
    baseline = baseline_bytes.decode("utf-8")
    manifest = json.loads((dataset_dir / "manifest.json").read_text(encoding="utf-8"))
    baseline_report = check_catalog(reference_catalog, dataset_dir, rules_path)
    if not baseline_report.valid:
        raise EvaluationSuiteError("Reference catalog must pass before faults are generated.")

    available = testcase_ids(baseline)
    selected = sorted(selected_testcases or available)
    unknown = sorted(set(selected) - set(available))
    if unknown:
        raise EvaluationSuiteError(f"Unknown test-case IDs: {', '.join(unknown)}")
    if not selected:
        raise EvaluationSuiteError("At least one test case must be selected.")

    output_dir.mkdir(parents=True, exist_ok=True)
    cases: list[dict[str, Any]] = []
    for testcase_id in selected:
        clean_id = f"clean-{testcase_id.lower()}"
        clean_report = _write_case(
            output_dir,
            clean_id,
            baseline_bytes,
            dataset_dir,
            rules_path,
        )
        cases.append(
            {
                "case_id": clean_id,
                "testcase_id": testcase_id,
                "fault_class": None,
                "expected_invalid": False,
                "checker_valid": clean_report.valid,
                "detected": not clean_report.valid,
                "issue_codes": sorted({issue.code for issue in clean_report.issues}),
                "catalog_sha256": sha256_bytes(baseline_bytes),
            }
        )

        for fault in FaultClass:
            case_id = f"{fault.value}-{testcase_id.lower()}"
            faulty, injection = inject_fault(baseline, fault, testcase_id, rules_path)
            faulty_bytes = faulty.encode("utf-8")
            report = _write_case(
                output_dir,
                case_id,
                faulty_bytes,
                dataset_dir,
                rules_path,
            )
            issue_codes = sorted({issue.code for issue in report.issues})
            cases.append(
                {
                    "case_id": case_id,
                    "testcase_id": testcase_id,
                    "fault_class": fault.value,
                    "expected_invalid": True,
                    "checker_valid": report.valid,
                    "detected": not report.valid,
                    "expected_issue_codes": list(injection.expected_issue_codes),
                    "issue_codes": issue_codes,
                    "catalog_sha256": sha256_bytes(faulty_bytes),
                }
            )

    suite = {
        "schema_version": "1.0",
        "suite_id": "catalog-checker-detection-v1",
        "dataset_id": manifest["dataset_id"],
        "source_hash": manifest["snapshot_hash"],
        "rules_sha256": sha256_bytes(rules_path.read_bytes()),
        "reference_catalog_sha256": sha256_bytes(baseline_bytes),
        "testcases": selected,
        "fault_classes": [fault.value for fault in FaultClass],
        "cases": cases,
        "metrics": confusion_metrics(cases),
    }
    (output_dir / "suite.json").write_bytes(pretty_json_bytes(suite))
    return suite

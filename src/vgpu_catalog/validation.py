"""Cross-file validation for a pinned synthetic dataset."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from vgpu_catalog.hashing import artifact_record, compute_snapshot_hash
from vgpu_catalog.schema_validation import iter_schema_errors


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    code: str
    path: str
    message: str
    expected: Any | None = None
    actual: Any | None = None


@dataclass(frozen=True, slots=True)
class ValidationReport:
    dataset_dir: str
    issues: tuple[ValidationIssue, ...]

    @property
    def valid(self) -> bool:
        return not self.issues

    def as_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "dataset_dir": self.dataset_dir,
            "issues": [asdict(issue) for issue in self.issues],
        }


def _duplicates(values: list[str]) -> list[str]:
    return sorted(value for value, count in Counter(values).items() if count > 1)


def _load_document(path: Path, issues: list[ValidationIssue]) -> dict[str, Any] | None:
    if not path.is_file():
        issues.append(
            ValidationIssue(
                code="FILE_MISSING",
                path=path.name,
                message="Required dataset file does not exist.",
            )
        )
        return None

    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        issues.append(
            ValidationIssue(
                code="INVALID_JSON",
                path=path.name,
                message=str(error),
            )
        )
        return None

    if not isinstance(value, dict):
        issues.append(
            ValidationIssue(
                code="INVALID_DOCUMENT",
                path=path.name,
                message="Top-level JSON value must be an object.",
            )
        )
        return None
    return value


def _add_schema_issues(
    schema_name: str,
    filename: str,
    document: dict[str, Any],
    issues: list[ValidationIssue],
) -> None:
    for message in iter_schema_errors(schema_name, document):
        issues.append(
            ValidationIssue(
                code="SCHEMA_ERROR",
                path=filename,
                message=message,
            )
        )


def _validate_identity(
    runs: dict[str, Any],
    capabilities: dict[str, Any],
    manifest: dict[str, Any],
    issues: list[ValidationIssue],
) -> None:
    ids = {
        "runs.json": runs.get("dataset_id"),
        "capabilities.json": capabilities.get("dataset_id"),
        "manifest.json": manifest.get("dataset_id"),
    }
    if len(set(ids.values())) != 1:
        issues.append(
            ValidationIssue(
                code="DATASET_ID_MISMATCH",
                path="dataset_id",
                message="All dataset files must use the same dataset_id.",
                actual=ids,
            )
        )

    timestamps = {
        "runs.json": runs.get("generated_at"),
        "capabilities.json": capabilities.get("generated_at"),
        "manifest.json": manifest.get("created_at"),
    }
    if len(set(timestamps.values())) != 1:
        issues.append(
            ValidationIssue(
                code="TIMESTAMP_MISMATCH",
                path="generated_at",
                message="Source generation times must match manifest created_at.",
                actual=timestamps,
            )
        )

    manifest_seed = manifest.get("generator", {}).get("seed")
    if runs.get("seed") != manifest_seed:
        issues.append(
            ValidationIssue(
                code="SEED_MISMATCH",
                path="manifest.json.generator.seed",
                message="Manifest seed must match runs.json seed.",
                expected=runs.get("seed"),
                actual=manifest_seed,
            )
        )


def _validate_references(
    runs: dict[str, Any],
    capabilities: dict[str, Any],
    issues: list[ValidationIssue],
) -> None:
    run_records = runs.get("runs", [])
    gpu_records = capabilities.get("gpus", [])
    testcase_records = capabilities.get("testcases", [])

    run_ids = [record.get("run_id") for record in run_records]
    gpu_ids = [record.get("gpu_id") for record in gpu_records]
    testcase_ids = [record.get("testcase_id") for record in testcase_records]

    for path, values in (
        ("runs.json.runs.run_id", run_ids),
        ("capabilities.json.gpus.gpu_id", gpu_ids),
        ("capabilities.json.testcases.testcase_id", testcase_ids),
    ):
        duplicates = _duplicates([value for value in values if isinstance(value, str)])
        if duplicates:
            issues.append(
                ValidationIssue(
                    code="DUPLICATE_ID",
                    path=path,
                    message="Identifiers must be unique.",
                    actual=duplicates,
                )
            )

    known_gpus = set(gpu_ids)
    known_testcases = set(testcase_ids)
    for index, run in enumerate(run_records):
        if run.get("gpu_id") not in known_gpus:
            issues.append(
                ValidationIssue(
                    code="UNKNOWN_GPU",
                    path=f"runs.json.runs.{index}.gpu_id",
                    message="Run references an undeclared GPU.",
                    actual=run.get("gpu_id"),
                )
            )
        if run.get("testcase_id") not in known_testcases:
            issues.append(
                ValidationIssue(
                    code="UNKNOWN_TESTCASE",
                    path=f"runs.json.runs.{index}.testcase_id",
                    message="Run references an undeclared test case.",
                    actual=run.get("testcase_id"),
                )
            )

        executed_at = run.get("executed_at")
        generated_at = runs.get("generated_at")
        if isinstance(executed_at, str) and isinstance(generated_at, str):
            executed = datetime.fromisoformat(executed_at.replace("Z", "+00:00"))
            generated = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
            if executed > generated:
                issues.append(
                    ValidationIssue(
                        code="RUN_AFTER_SNAPSHOT",
                        path=f"runs.json.runs.{index}.executed_at",
                        message="A run cannot occur after snapshot generation.",
                        expected=f"<= {generated_at}",
                        actual=executed_at,
                    )
                )


def _validate_artifacts(
    dataset_dir: Path,
    manifest: dict[str, Any],
    issues: list[ValidationIssue],
) -> None:
    declared_records = {
        record.get("path"): record
        for record in manifest.get("artifacts", [])
        if isinstance(record, dict) and isinstance(record.get("path"), str)
    }
    actual_records: list[dict[str, str | int]] = []

    for filename in ("capabilities.json", "runs.json"):
        path = dataset_dir / filename
        if not path.is_file():
            continue

        actual = artifact_record(path)
        actual_records.append(actual)
        declared = declared_records.get(filename)
        if declared is None:
            issues.append(
                ValidationIssue(
                    code="ARTIFACT_NOT_DECLARED",
                    path=f"manifest.json.artifacts.{filename}",
                    message="Source artifact is missing from the manifest.",
                )
            )
            continue

        for field in ("bytes", "sha256"):
            if declared.get(field) != actual[field]:
                issues.append(
                    ValidationIssue(
                        code=f"ARTIFACT_{field.upper()}_MISMATCH",
                        path=f"manifest.json.artifacts.{filename}.{field}",
                        message=f"Declared {field} does not match source bytes.",
                        expected=actual[field],
                        actual=declared.get(field),
                    )
                )

    if len(actual_records) == 2:
        actual_snapshot_hash = compute_snapshot_hash(actual_records)
        if manifest.get("snapshot_hash") != actual_snapshot_hash:
            issues.append(
                ValidationIssue(
                    code="SNAPSHOT_HASH_MISMATCH",
                    path="manifest.json.snapshot_hash",
                    message="Snapshot hash does not match the current source artifacts.",
                    expected=actual_snapshot_hash,
                    actual=manifest.get("snapshot_hash"),
                )
            )


def validate_dataset(dataset_dir: Path) -> ValidationReport:
    dataset_dir = dataset_dir.resolve()
    issues: list[ValidationIssue] = []
    documents = {
        "runs": _load_document(dataset_dir / "runs.json", issues),
        "capabilities": _load_document(dataset_dir / "capabilities.json", issues),
        "manifest": _load_document(dataset_dir / "manifest.json", issues),
    }

    for name, document in documents.items():
        if document is not None:
            _add_schema_issues(name, f"{name}.json", document, issues)

    schemas_valid = not any(issue.code == "SCHEMA_ERROR" for issue in issues)
    if all(document is not None for document in documents.values()) and schemas_valid:
        runs = documents["runs"]
        capabilities = documents["capabilities"]
        manifest = documents["manifest"]
        assert runs is not None and capabilities is not None and manifest is not None
        _validate_identity(runs, capabilities, manifest, issues)
        _validate_references(runs, capabilities, issues)
        _validate_artifacts(dataset_dir, manifest, issues)

    return ValidationReport(dataset_dir=str(dataset_dir), issues=tuple(issues))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset_dir", nargs="?", type=Path, default=Path("dataset"))
    args = parser.parse_args()

    report = validate_dataset(args.dataset_dir)
    print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2))
    return 0 if report.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())

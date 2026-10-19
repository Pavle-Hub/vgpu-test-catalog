import json
from pathlib import Path

from vgpu_catalog.dataset import (
    DEFAULT_RUNS_PER_PAIR,
    DEFAULT_SPARSE_SAMPLES,
    SPARSE_PAIR,
    generate_documents,
    write_dataset,
)
from vgpu_catalog.hashing import artifact_record, compute_snapshot_hash, pretty_json_bytes
from vgpu_catalog.validation import validate_dataset


def _refresh_manifest(dataset_dir: Path) -> None:
    manifest_path = dataset_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    artifacts = [
        artifact_record(dataset_dir / filename) for filename in ("capabilities.json", "runs.json")
    ]
    manifest["artifacts"] = artifacts
    manifest["snapshot_hash"] = compute_snapshot_hash(artifacts)
    manifest_path.write_bytes(pretty_json_bytes(manifest))


def test_default_dataset_has_expected_shape() -> None:
    runs, capabilities = generate_documents()

    assert len(capabilities["gpus"]) == 3
    assert len(capabilities["testcases"]) == 10
    assert len(runs["runs"]) == 545

    sparse_runs = [
        run for run in runs["runs"] if (run["testcase_id"], run["gpu_id"]) == SPARSE_PAIR
    ]
    assert len(sparse_runs) == DEFAULT_SPARSE_SAMPLES

    regular_runs = [
        run for run in runs["runs"] if run["testcase_id"] == "TC-001" and run["gpu_id"] == "GPU-A"
    ]
    assert len(regular_runs) == DEFAULT_RUNS_PER_PAIR


def test_same_parameters_produce_identical_artifact_bytes(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"

    write_dataset(first)
    write_dataset(second)

    for filename in ("runs.json", "capabilities.json", "manifest.json"):
        assert (first / filename).read_bytes() == (second / filename).read_bytes()


def test_different_seed_changes_snapshot_hash(tmp_path: Path) -> None:
    first_manifest = write_dataset(tmp_path / "first", seed=2026)
    second_manifest = write_dataset(tmp_path / "second", seed=2027)

    assert first_manifest["snapshot_hash"] != second_manifest["snapshot_hash"]


def test_generated_dataset_passes_cross_file_validation(tmp_path: Path) -> None:
    dataset_dir = tmp_path / "dataset"
    write_dataset(dataset_dir)

    report = validate_dataset(dataset_dir)

    assert report.valid
    assert report.issues == ()


def test_validator_detects_source_tampering(tmp_path: Path) -> None:
    dataset_dir = tmp_path / "dataset"
    write_dataset(dataset_dir)
    runs_path = dataset_dir / "runs.json"
    runs = json.loads(runs_path.read_text(encoding="utf-8"))
    runs["runs"][0]["duration_seconds"] += 1
    runs_path.write_bytes(pretty_json_bytes(runs))

    report = validate_dataset(dataset_dir)
    codes = {issue.code for issue in report.issues}

    assert not report.valid
    assert "ARTIFACT_SHA256_MISMATCH" in codes
    assert "SNAPSHOT_HASH_MISMATCH" in codes


def test_validator_detects_unknown_gpu_with_valid_provenance(tmp_path: Path) -> None:
    dataset_dir = tmp_path / "dataset"
    write_dataset(dataset_dir)
    runs_path = dataset_dir / "runs.json"
    runs = json.loads(runs_path.read_text(encoding="utf-8"))
    runs["runs"][0]["gpu_id"] = "GPU-Z"
    runs_path.write_bytes(pretty_json_bytes(runs))
    _refresh_manifest(dataset_dir)

    report = validate_dataset(dataset_dir)
    codes = {issue.code for issue in report.issues}

    assert not report.valid
    assert codes == {"UNKNOWN_GPU"}


def test_validator_detects_duplicate_run_identifier(tmp_path: Path) -> None:
    dataset_dir = tmp_path / "dataset"
    write_dataset(dataset_dir)
    runs_path = dataset_dir / "runs.json"
    runs = json.loads(runs_path.read_text(encoding="utf-8"))
    runs["runs"][1]["run_id"] = runs["runs"][0]["run_id"]
    runs_path.write_bytes(pretty_json_bytes(runs))
    _refresh_manifest(dataset_dir)

    report = validate_dataset(dataset_dir)

    assert not report.valid
    assert {issue.code for issue in report.issues} == {"DUPLICATE_ID"}

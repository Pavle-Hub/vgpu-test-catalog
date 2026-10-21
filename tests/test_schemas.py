import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError

SCHEMA_DIR = Path(__file__).parents[1] / "schemas"


def load_schema(name: str) -> dict:
    return json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def valid_runs() -> dict:
    return {
        "schema_version": "1.0",
        "dataset_id": "dataset-reference-2026",
        "seed": 2026,
        "generated_at": "2026-01-01T00:00:00Z",
        "runs": [
            {
                "run_id": "run-00000001",
                "testcase_id": "TC-001",
                "gpu_id": "GPU-A",
                "status": "passed",
                "duration_seconds": 42.5,
                "iterations": 100,
                "executed_at": "2025-12-31T23:00:00Z",
            }
        ],
    }


@pytest.fixture(scope="module")
def valid_capabilities() -> dict:
    return {
        "schema_version": "1.0",
        "dataset_id": "dataset-reference-2026",
        "generated_at": "2026-01-01T00:00:00Z",
        "gpus": [
            {
                "gpu_id": "GPU-A",
                "capabilities": ["compute-basic", "graphics"],
            }
        ],
        "testcases": [
            {
                "testcase_id": "TC-001",
                "required_capabilities": ["compute-basic"],
            }
        ],
    }


@pytest.fixture(scope="module")
def valid_manifest() -> dict:
    return {
        "schema_version": "1.0",
        "dataset_id": "dataset-reference-2026",
        "created_at": "2026-01-01T00:00:00Z",
        "generator": {"name": "gen_dataset", "version": "0.1.0", "seed": 2026},
        "artifacts": [
            {"path": "runs.json", "bytes": 1024, "sha256": "a" * 64},
            {"path": "capabilities.json", "bytes": 512, "sha256": "b" * 64},
        ],
        "snapshot_hash": "c" * 64,
    }


@pytest.mark.parametrize(
    "schema_name",
    [
        "runs.schema.json",
        "capabilities.schema.json",
        "manifest.schema.json",
        "rules.schema.json",
    ],
)
def test_schema_is_valid_draft_2020_12(schema_name: str) -> None:
    Draft202012Validator.check_schema(load_schema(schema_name))


def test_valid_runs_document(valid_runs: dict) -> None:
    Draft202012Validator(load_schema("runs.schema.json")).validate(valid_runs)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("run_id", "run-one"),
        ("testcase_id", "test-1"),
        ("gpu_id", "A100"),
        ("status", "unknown"),
        ("duration_seconds", 0),
        ("iterations", 0),
    ],
)
def test_invalid_run_field_is_rejected(valid_runs: dict, field: str, value: object) -> None:
    document = copy.deepcopy(valid_runs)
    document["runs"][0][field] = value

    with pytest.raises(ValidationError):
        Draft202012Validator(load_schema("runs.schema.json")).validate(document)


def test_unknown_run_field_is_rejected(valid_runs: dict) -> None:
    document = copy.deepcopy(valid_runs)
    document["runs"][0]["agent_guess"] = True

    with pytest.raises(ValidationError):
        Draft202012Validator(load_schema("runs.schema.json")).validate(document)


def test_valid_capability_document(valid_capabilities: dict) -> None:
    Draft202012Validator(load_schema("capabilities.schema.json")).validate(valid_capabilities)


def test_duplicate_capability_is_rejected(valid_capabilities: dict) -> None:
    document = copy.deepcopy(valid_capabilities)
    document["gpus"][0]["capabilities"] = ["graphics", "graphics"]

    with pytest.raises(ValidationError):
        Draft202012Validator(load_schema("capabilities.schema.json")).validate(document)


def test_unknown_capability_is_rejected(valid_capabilities: dict) -> None:
    document = copy.deepcopy(valid_capabilities)
    document["testcases"][0]["required_capabilities"] = ["telepathy"]

    with pytest.raises(ValidationError):
        Draft202012Validator(load_schema("capabilities.schema.json")).validate(document)


def test_valid_manifest_document(valid_manifest: dict) -> None:
    Draft202012Validator(load_schema("manifest.schema.json")).validate(valid_manifest)


def test_manifest_requires_both_artifacts(valid_manifest: dict) -> None:
    document = copy.deepcopy(valid_manifest)
    document["artifacts"][1]["path"] = "runs.json"

    with pytest.raises(ValidationError):
        Draft202012Validator(load_schema("manifest.schema.json")).validate(document)


def test_manifest_rejects_non_sha256_digest(valid_manifest: dict) -> None:
    document = copy.deepcopy(valid_manifest)
    document["snapshot_hash"] = "not-a-sha256"

    with pytest.raises(ValidationError):
        Draft202012Validator(load_schema("manifest.schema.json")).validate(document)

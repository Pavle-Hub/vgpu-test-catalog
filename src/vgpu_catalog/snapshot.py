"""Validated loading of the repository-pinned source snapshot."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from vgpu_catalog.schema_validation import PROJECT_ROOT
from vgpu_catalog.validation import validate_dataset

DEFAULT_DATASET_DIR = PROJECT_ROOT / "dataset"


class SnapshotError(ValueError):
    """Raised when a source snapshot cannot be used safely."""


@dataclass(frozen=True, slots=True)
class DatasetSnapshot:
    directory: Path
    runs: dict[str, Any]
    capabilities: dict[str, Any]
    manifest: dict[str, Any]

    @property
    def dataset_id(self) -> str:
        return self.manifest["dataset_id"]

    @property
    def source_hash(self) -> str:
        return self.manifest["snapshot_hash"]

    @property
    def snapshot_at(self) -> str:
        return self.manifest["created_at"]


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_snapshot(dataset_dir: Path = DEFAULT_DATASET_DIR) -> DatasetSnapshot:
    """Validate all snapshot invariants before returning source documents."""

    dataset_dir = dataset_dir.resolve()
    report = validate_dataset(dataset_dir)
    if not report.valid:
        details = "; ".join(
            f"{issue.code}: {issue.path}: {issue.message}" for issue in report.issues
        )
        raise SnapshotError(f"Dataset validation failed: {details}")

    return DatasetSnapshot(
        directory=dataset_dir,
        runs=_load_json(dataset_dir / "runs.json"),
        capabilities=_load_json(dataset_dir / "capabilities.json"),
        manifest=_load_json(dataset_dir / "manifest.json"),
    )

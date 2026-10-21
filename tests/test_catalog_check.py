from pathlib import Path
from shutil import copyfile

import pytest

from catalog_check.checker import CatalogWriteError, check_catalog, write_catalog
from catalog_check.markdown import BLOCK_PATTERN, find_blocks

REFERENCE_CATALOG = Path("catalog/test_catalog.md")
DATASET_DIR = Path("dataset")


def _catalog_copy(tmp_path: Path) -> Path:
    target = tmp_path / "test_catalog.md"
    copyfile(REFERENCE_CATALOG, target)
    return target


def test_committed_catalog_matches_deterministic_derivation() -> None:
    report = check_catalog(REFERENCE_CATALOG, DATASET_DIR)

    assert report.valid
    assert report.issues == ()


def test_checker_detects_visible_markdown_drift(tmp_path: Path) -> None:
    catalog_path = _catalog_copy(tmp_path)
    document = catalog_path.read_text(encoding="utf-8")
    catalog_path.write_text(document.replace("`26 s`", "`999 s`", 1), encoding="utf-8")

    report = check_catalog(catalog_path, DATASET_DIR)

    assert not report.valid
    assert "MARKDOWN_DRIFT" in {issue.code for issue in report.issues}


def test_checker_detects_wrong_provenance_hash(tmp_path: Path) -> None:
    catalog_path = _catalog_copy(tmp_path)
    document = catalog_path.read_text(encoding="utf-8")
    catalog_path.write_text(
        document.replace(
            "83c9a22581b017a0ebc967d7c5bd4ef53f6c9edcb246e696ab402314a5eef394",
            "0" * 64,
            1,
        ),
        encoding="utf-8",
    )

    report = check_catalog(catalog_path, DATASET_DIR)
    codes = {issue.code for issue in report.issues}

    assert not report.valid
    assert "FIELD_MISMATCH" in codes
    assert "MARKDOWN_DRIFT" in codes


def test_checker_rederives_internally_consistent_but_stale_value(tmp_path: Path) -> None:
    catalog_path = _catalog_copy(tmp_path)
    document = catalog_path.read_text(encoding="utf-8")
    document = document.replace("**Timeout:** `26 s`", "**Timeout:** `25 s`", 1)
    document = document.replace('"value": 26', '"value": 25', 1)
    catalog_path.write_text(document, encoding="utf-8")

    report = check_catalog(catalog_path, DATASET_DIR)

    assert any(
        issue.code == "FIELD_MISMATCH" and issue.path == "TC-001.fields.timeout_seconds.value"
        for issue in report.issues
    )
    assert "MARKDOWN_DRIFT" in {issue.code for issue in report.issues}


def test_checker_validates_machine_block_schema(tmp_path: Path) -> None:
    catalog_path = _catalog_copy(tmp_path)
    document = catalog_path.read_text(encoding="utf-8")
    catalog_path.write_text(
        document.replace('"format_version": "1.0"', '"format_version": "2.0"', 1),
        encoding="utf-8",
    )

    report = check_catalog(catalog_path, DATASET_DIR)

    assert "DERIVED_SCHEMA_ERROR" in {issue.code for issue in report.issues}


def test_checker_applies_weak_semantic_summary_constraint(tmp_path: Path) -> None:
    catalog_path = _catalog_copy(tmp_path)
    document = catalog_path.read_text(encoding="utf-8")
    catalog_path.write_text(
        document.replace(
            "Baseline compute currently has measurements across all compatible GPU models.",
            "Too short.",
            1,
        ),
        encoding="utf-8",
    )

    report = check_catalog(catalog_path, DATASET_DIR)

    assert "SEMANTIC_FIELD_LENGTH" in {issue.code for issue in report.issues}


def test_write_repairs_derived_block_and_preserves_surrounding_text(tmp_path: Path) -> None:
    catalog_path = _catalog_copy(tmp_path)
    document = catalog_path.read_text(encoding="utf-8")
    document = document.replace("`26 s`", "`999 s`", 1)
    document = document.replace('"value": 26', '"value": 999', 1)
    document = document.replace(
        "Verify the baseline compute path required by every synthetic vGPU workload.",
        "CUSTOM HUMAN PURPOSE THAT MUST SURVIVE.",
        1,
    )
    catalog_path.write_text(document, encoding="utf-8")
    before = catalog_path.read_text(encoding="utf-8")

    report, changed = write_catalog(catalog_path, DATASET_DIR)
    after = catalog_path.read_text(encoding="utf-8")

    assert changed
    assert report.valid
    assert "`26 s`" in after
    assert "`999 s`" not in after
    assert "CUSTOM HUMAN PURPOSE THAT MUST SURVIVE." in after
    assert BLOCK_PATTERN.sub("<DERIVED BLOCK>", before) == BLOCK_PATTERN.sub(
        "<DERIVED BLOCK>", after
    )


def test_write_refuses_catalog_with_missing_block(tmp_path: Path) -> None:
    catalog_path = _catalog_copy(tmp_path)
    document = catalog_path.read_text(encoding="utf-8")
    first_block = find_blocks(document)[0]
    catalog_path.write_text(
        document[: first_block.start] + document[first_block.end :],
        encoding="utf-8",
    )

    with pytest.raises(CatalogWriteError, match="Refusing --write"):
        write_catalog(catalog_path, DATASET_DIR)


def test_write_refuses_block_moved_outside_derived_subsection(tmp_path: Path) -> None:
    catalog_path = _catalog_copy(tmp_path)
    document = catalog_path.read_text(encoding="utf-8")
    first_block = find_blocks(document)[0]
    block_text = first_block.text
    without_block = document[: first_block.start] + document[first_block.end :]
    moved = without_block.replace("### Purpose\n", f"### Purpose\n\n{block_text}\n", 1)
    catalog_path.write_text(moved, encoding="utf-8")

    with pytest.raises(CatalogWriteError, match="Refusing --write"):
        write_catalog(catalog_path, DATASET_DIR)

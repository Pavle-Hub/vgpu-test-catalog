"""Deterministic checking and bounded mechanical repair of the Markdown catalog."""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from catalog_check.markdown import (
    CatalogBlock,
    CatalogBlockError,
    derived_block_data,
    find_blocks,
    marker_ids,
    normalize_newlines,
    parse_derived_block,
    render_derived_block,
)
from vgpu_catalog.derivation import derive_catalog
from vgpu_catalog.rules import DEFAULT_RULES_PATH, CatalogRules, load_rules
from vgpu_catalog.schema_validation import iter_schema_errors

SECTION_PATTERN = re.compile(r"^## (?P<testcase_id>TC-[0-9]{3})\s*$", re.MULTILINE)
FIELD_PATTERN = re.compile(r"^### (?P<name>[^\r\n]+?)\s*$", re.MULTILINE)


class CatalogWriteError(ValueError):
    """Raised when --write cannot safely preserve non-derived content."""


@dataclass(frozen=True, slots=True)
class CatalogIssue:
    code: str
    path: str
    message: str
    expected: Any | None = None
    actual: Any | None = None


@dataclass(frozen=True, slots=True)
class CatalogReport:
    catalog_path: str
    dataset_dir: str
    issues: tuple[CatalogIssue, ...]

    @property
    def valid(self) -> bool:
        return not self.issues

    def as_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "catalog_path": self.catalog_path,
            "dataset_dir": self.dataset_dir,
            "issues": [asdict(issue) for issue in self.issues],
        }


@dataclass(frozen=True, slots=True)
class CatalogSection:
    testcase_id: str
    start: int
    end: int
    text: str


def _find_sections(document: str) -> list[CatalogSection]:
    matches = list(SECTION_PATTERN.finditer(document))
    return [
        CatalogSection(
            testcase_id=match.group("testcase_id"),
            start=match.start(),
            end=matches[index + 1].start() if index + 1 < len(matches) else len(document),
            text=document[match.start() : matches[index + 1].start()]
            if index + 1 < len(matches)
            else document[match.start() :],
        )
        for index, match in enumerate(matches)
    ]


def _section_fields(section: CatalogSection) -> dict[str, list[str]]:
    matches = list(FIELD_PATTERN.finditer(section.text))
    values: dict[str, list[str]] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(section.text)
        values.setdefault(match.group("name"), []).append(section.text[match.end() : end].strip())
    return values


def _section_field_spans(section: CatalogSection) -> dict[str, list[tuple[int, int]]]:
    matches = list(FIELD_PATTERN.finditer(section.text))
    spans: dict[str, list[tuple[int, int]]] = {}
    for index, match in enumerate(matches):
        relative_end = matches[index + 1].start() if index + 1 < len(matches) else len(section.text)
        spans.setdefault(match.group("name"), []).append(
            (section.start + match.end(), section.start + relative_end)
        )
    return spans


def _compare_values(
    expected: Any,
    actual: Any,
    path: str,
    tolerance: Decimal,
    issues: list[CatalogIssue],
) -> None:
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            issues.append(
                CatalogIssue("FIELD_MISMATCH", path, "Expected a JSON object.", expected, actual)
            )
            return
        for key in sorted(expected.keys() | actual.keys()):
            child_path = f"{path}.{key}"
            if key not in actual:
                issues.append(
                    CatalogIssue("FIELD_MISSING", child_path, "Expected field is missing.")
                )
            elif key not in expected:
                issues.append(
                    CatalogIssue("FIELD_UNKNOWN", child_path, "Unexpected field is present.")
                )
            else:
                _compare_values(expected[key], actual[key], child_path, tolerance, issues)
        return

    if isinstance(expected, list):
        if expected != actual:
            issues.append(
                CatalogIssue("FIELD_MISMATCH", path, "Array value differs.", expected, actual)
            )
        return

    numeric = (
        isinstance(expected, (int, float))
        and not isinstance(expected, bool)
        and isinstance(actual, (int, float))
        and not isinstance(actual, bool)
    )
    if numeric:
        difference = abs(Decimal(str(expected)) - Decimal(str(actual)))
        if difference > tolerance:
            issues.append(
                CatalogIssue("FIELD_MISMATCH", path, "Numeric value differs.", expected, actual)
            )
    elif expected != actual:
        issues.append(CatalogIssue("FIELD_MISMATCH", path, "Value differs.", expected, actual))


def _add_structure_issues(
    document: str,
    expected_ids: set[str],
    rules: CatalogRules,
    issues: list[CatalogIssue],
) -> tuple[list[CatalogBlock], list[CatalogSection]]:
    starts, ends = marker_ids(document)
    start_counts = Counter(starts)
    end_counts = Counter(ends)
    sections = _find_sections(document)
    section_counts = Counter(section.testcase_id for section in sections)

    for testcase_id in sorted(expected_ids):
        if section_counts[testcase_id] != 1:
            issues.append(
                CatalogIssue(
                    "SECTION_COUNT",
                    testcase_id,
                    "Each expected test case must have exactly one level-two section.",
                    1,
                    section_counts[testcase_id],
                )
            )
        if start_counts[testcase_id] != 1 or end_counts[testcase_id] != 1:
            issues.append(
                CatalogIssue(
                    "MARKER_COUNT",
                    testcase_id,
                    "Each test case must have exactly one matching derived block.",
                    {"start": 1, "end": 1},
                    {"start": start_counts[testcase_id], "end": end_counts[testcase_id]},
                )
            )

    observed_ids = set(starts) | set(ends) | set(section_counts)
    for testcase_id in sorted(observed_ids - expected_ids):
        issues.append(
            CatalogIssue(
                "UNKNOWN_TESTCASE",
                testcase_id,
                "Catalog contains a test case absent from the pinned capability matrix.",
            )
        )

    required_fields = ("Purpose", "Notes", "Derived fields", "Summary")
    minimum = rules.catalog.semantic_summary.minimum_characters
    maximum = rules.catalog.semantic_summary.maximum_characters
    for section in sections:
        if section.testcase_id not in expected_ids or section_counts[section.testcase_id] != 1:
            continue
        fields = _section_fields(section)
        for field in required_fields:
            values = fields.get(field, [])
            if len(values) != 1:
                issues.append(
                    CatalogIssue(
                        "SECTION_FIELD_COUNT",
                        f"{section.testcase_id}.{field}",
                        "Required section field must occur exactly once.",
                        1,
                        len(values),
                    )
                )
            elif field in {"Purpose", "Notes"} and not values[0]:
                issues.append(
                    CatalogIssue(
                        "HUMAN_FIELD_EMPTY",
                        f"{section.testcase_id}.{field}",
                        "Human-authored field must not be empty.",
                    )
                )

        summaries = fields.get("Summary", [])
        if len(summaries) == 1 and not minimum <= len(summaries[0]) <= maximum:
            issues.append(
                CatalogIssue(
                    "SEMANTIC_FIELD_LENGTH",
                    f"{section.testcase_id}.Summary",
                    "Semantic summary length is outside the declared bounds.",
                    {"minimum": minimum, "maximum": maximum},
                    len(summaries[0]),
                )
            )

    blocks = find_blocks(document)
    block_counts = Counter(block.testcase_id for block in blocks)
    for testcase_id in sorted(expected_ids):
        if (
            start_counts[testcase_id] == 1
            and end_counts[testcase_id] == 1
            and block_counts[testcase_id] != 1
        ):
            issues.append(
                CatalogIssue(
                    "BLOCK_PAIRING",
                    testcase_id,
                    "Derived start and end markers are not a valid matching pair.",
                )
            )

    section_by_id = {
        section.testcase_id: section
        for section in sections
        if section_counts[section.testcase_id] == 1
    }
    for block in blocks:
        section = section_by_id.get(block.testcase_id)
        if section is not None and not (section.start <= block.start and block.end <= section.end):
            issues.append(
                CatalogIssue(
                    "BLOCK_OUTSIDE_SECTION",
                    block.testcase_id,
                    "Derived block must be inside its matching test-case section.",
                )
            )
        elif section is not None:
            derived_spans = _section_field_spans(section).get("Derived fields", [])
            if len(derived_spans) == 1 and not (
                derived_spans[0][0] <= block.start and block.end <= derived_spans[0][1]
            ):
                issues.append(
                    CatalogIssue(
                        "BLOCK_OUTSIDE_DERIVED_FIELD",
                        block.testcase_id,
                        "Derived block must be inside the Derived fields subsection.",
                    )
                )

    return blocks, sections


def check_catalog(
    catalog_path: Path,
    dataset_dir: Path,
    rules_path: Path = DEFAULT_RULES_PATH,
) -> CatalogReport:
    """Re-derive expected state and compare it with the committed catalog."""

    catalog_path = catalog_path.resolve()
    dataset_dir = dataset_dir.resolve()
    issues: list[CatalogIssue] = []
    if not catalog_path.is_file():
        issues.append(
            CatalogIssue("FILE_MISSING", catalog_path.name, "Catalog file does not exist.")
        )
        return CatalogReport(str(catalog_path), str(dataset_dir), tuple(issues))

    try:
        document = catalog_path.read_bytes().decode("utf-8")
    except UnicodeDecodeError as error:
        issues.append(CatalogIssue("INVALID_UTF8", catalog_path.name, str(error)))
        return CatalogReport(str(catalog_path), str(dataset_dir), tuple(issues))

    rules = load_rules(rules_path)
    expected = derive_catalog(dataset_dir, rules_path)
    expected_by_id = {item["testcase_id"]: item for item in expected["testcases"]}
    blocks, _ = _add_structure_issues(document, set(expected_by_id), rules, issues)
    block_counts = Counter(block.testcase_id for block in blocks)

    for block in blocks:
        if block.testcase_id not in expected_by_id or block_counts[block.testcase_id] != 1:
            continue
        expected_testcase = expected_by_id[block.testcase_id]
        try:
            actual_data = parse_derived_block(block)
        except CatalogBlockError as error:
            issues.append(CatalogIssue("DERIVED_DATA_INVALID", block.testcase_id, str(error)))
        else:
            schema_errors = iter_schema_errors("catalog_derived", actual_data)
            for message in schema_errors:
                issues.append(CatalogIssue("DERIVED_SCHEMA_ERROR", block.testcase_id, message))
            if not schema_errors:
                expected_data = derived_block_data(expected_testcase, rules)
                _compare_values(
                    expected_data,
                    actual_data,
                    block.testcase_id,
                    rules.comparison.numeric_tolerance,
                    issues,
                )

        expected_block = render_derived_block(expected_testcase, rules)
        if normalize_newlines(block.text) != expected_block:
            issues.append(
                CatalogIssue(
                    "MARKDOWN_DRIFT",
                    block.testcase_id,
                    "Visible or hidden derived Markdown differs from deterministic output.",
                )
            )

    issues.sort(key=lambda issue: (issue.path, issue.code, issue.message))
    return CatalogReport(str(catalog_path), str(dataset_dir), tuple(issues))


def _validate_writable_structure(
    document: str,
    expected_ids: set[str],
) -> list[CatalogBlock]:
    starts, ends = marker_ids(document)
    start_counts = Counter(starts)
    end_counts = Counter(ends)
    blocks = find_blocks(document)
    block_counts = Counter(block.testcase_id for block in blocks)
    sections = _find_sections(document)
    section_counts = Counter(section.testcase_id for section in sections)
    section_by_id = {section.testcase_id: section for section in sections}
    blocks_in_derived_fields = all(
        len(_section_field_spans(section_by_id[block.testcase_id]).get("Derived fields", [])) == 1
        and _section_field_spans(section_by_id[block.testcase_id])["Derived fields"][0][0]
        <= block.start
        and block.end
        <= _section_field_spans(section_by_id[block.testcase_id])["Derived fields"][0][1]
        for block in blocks
        if block.testcase_id in section_by_id
    )

    safe = (
        set(start_counts) == expected_ids
        and set(end_counts) == expected_ids
        and set(block_counts) == expected_ids
        and set(section_counts) == expected_ids
        and blocks_in_derived_fields
        and all(
            start_counts[testcase_id]
            == end_counts[testcase_id]
            == block_counts[testcase_id]
            == section_counts[testcase_id]
            == 1
            for testcase_id in expected_ids
        )
    )
    if not safe:
        raise CatalogWriteError(
            "Refusing --write because catalog sections or derived markers are missing, "
            "duplicated, unknown, or mismatched."
        )
    return blocks


def write_catalog(
    catalog_path: Path,
    dataset_dir: Path,
    rules_path: Path = DEFAULT_RULES_PATH,
) -> tuple[CatalogReport, bool]:
    """Replace only validated derived blocks and leave all surrounding text intact."""

    catalog_path = catalog_path.resolve()
    if not catalog_path.is_file():
        raise CatalogWriteError("Catalog must exist before --write can update derived fields.")

    try:
        document = catalog_path.read_bytes().decode("utf-8")
    except UnicodeDecodeError as error:
        raise CatalogWriteError(f"Catalog is not valid UTF-8: {error}") from error

    rules = load_rules(rules_path)
    expected = derive_catalog(dataset_dir, rules_path)
    expected_by_id = {item["testcase_id"]: item for item in expected["testcases"]}
    blocks = _validate_writable_structure(document, set(expected_by_id))
    newline = "\r\n" if "\r\n" in document else "\n"

    pieces: list[str] = []
    cursor = 0
    for block in sorted(blocks, key=lambda item: item.start):
        pieces.append(document[cursor : block.start])
        rendered = render_derived_block(expected_by_id[block.testcase_id], rules)
        pieces.append(rendered.replace("\n", newline))
        cursor = block.end
    pieces.append(document[cursor:])
    updated = "".join(pieces)
    changed = updated != document

    if changed:
        temporary = catalog_path.with_name(f".{catalog_path.name}.tmp")
        temporary.write_bytes(updated.encode("utf-8"))
        temporary.replace(catalog_path)

    return check_catalog(catalog_path, dataset_dir, rules_path), changed


def report_json(report: CatalogReport, *, mode: str, written: bool | None = None) -> str:
    value = {"mode": mode, **report.as_dict()}
    if written is not None:
        value["written"] = written
    return json.dumps(value, ensure_ascii=False, indent=2)

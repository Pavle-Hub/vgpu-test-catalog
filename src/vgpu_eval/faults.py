"""Deterministic catalog fault operators used by the evaluation framework."""

from __future__ import annotations

import copy
import json
import re
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from catalog_check.markdown import (
    DATA_PATTERN,
    find_blocks,
    parse_derived_block,
    render_derived_block,
)
from vgpu_catalog.rules import DEFAULT_RULES_PATH, load_rules


class FaultInjectionError(ValueError):
    """Raised when a requested fault cannot be injected unambiguously."""


class FaultClass(StrEnum):
    WRONG_VALUE = "wrong-value"
    STALE_VALUE = "stale-value"
    HALLUCINATED_FIELD = "hallucinated-field"
    BROKEN_FORMAT = "broken-format"
    FALSE_PROVENANCE = "false-provenance"


@dataclass(frozen=True, slots=True)
class FaultInjection:
    fault_class: str
    testcase_id: str
    changed_path: str
    original: Any
    injected: Any
    expected_issue_codes: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["expected_issue_codes"] = list(self.expected_issue_codes)
        return value


def testcase_ids(document: str) -> list[str]:
    """Return sorted, unique test-case IDs that have complete derived blocks."""

    identifiers = [block.testcase_id for block in find_blocks(document)]
    if len(identifiers) != len(set(identifiers)):
        raise FaultInjectionError("Catalog contains duplicate derived blocks.")
    return sorted(identifiers)


def _machine_data(block_text: str, data: dict[str, Any]) -> str:
    matches = list(DATA_PATTERN.finditer(block_text))
    if len(matches) != 1:
        raise FaultInjectionError("Target block must contain exactly one machine-data comment.")
    rendered = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)
    replacement = f"<!-- catalog:derived-data\n{rendered}\n-->"
    match = matches[0]
    return block_text[: match.start()] + replacement + block_text[match.end() :]


def _render(testcase_id: str, data: dict[str, Any], rules_path: Path) -> str:
    fields = data["fields"]
    testcase = {"testcase_id": testcase_id, **fields}
    return render_derived_block(testcase, load_rules(rules_path))


def _wrong_value(
    testcase_id: str,
    data: dict[str, Any],
    rules_path: Path,
) -> tuple[str, FaultInjection]:
    timeout = data["fields"]["timeout_seconds"]
    original = timeout["value"]
    timeout["value"] = original + 7 if isinstance(original, int) else 1
    timeout["status"] = "ok"
    return _render(testcase_id, data, rules_path), FaultInjection(
        fault_class=FaultClass.WRONG_VALUE,
        testcase_id=testcase_id,
        changed_path=f"{testcase_id}.fields.timeout_seconds.value",
        original=original,
        injected=timeout["value"],
        expected_issue_codes=("FIELD_MISMATCH", "MARKDOWN_DRIFT"),
    )


def _stale_value(
    testcase_id: str,
    data: dict[str, Any],
    rules_path: Path,
) -> tuple[str, FaultInjection]:
    last_measurement = data["fields"]["last_measurement"]
    original = {
        "value": last_measurement["value"],
        "status": last_measurement["status"],
    }
    last_measurement["value"] = "2000-01-01T00:00:00Z"
    last_measurement["status"] = "stale"
    injected = {
        "value": last_measurement["value"],
        "status": last_measurement["status"],
    }
    return _render(testcase_id, data, rules_path), FaultInjection(
        fault_class=FaultClass.STALE_VALUE,
        testcase_id=testcase_id,
        changed_path=f"{testcase_id}.fields.last_measurement",
        original=original,
        injected=injected,
        expected_issue_codes=("FIELD_MISMATCH", "MARKDOWN_DRIFT"),
    )


def _hallucinated_field(
    testcase_id: str,
    data: dict[str, Any],
    rules_path: Path,
) -> tuple[str, FaultInjection]:
    original_data = copy.deepcopy(data)
    data["fields"]["agent_confidence"] = {"value": "high"}
    rendered = _render(testcase_id, original_data, rules_path)
    rendered = rendered.replace(
        "<!-- catalog:derived-data",
        "- **Agent confidence:** `high`\n<!-- catalog:derived-data",
        1,
    )
    rendered = _machine_data(rendered, data)
    return rendered, FaultInjection(
        fault_class=FaultClass.HALLUCINATED_FIELD,
        testcase_id=testcase_id,
        changed_path=f"{testcase_id}.fields.agent_confidence",
        original=None,
        injected={"value": "high"},
        expected_issue_codes=("DERIVED_SCHEMA_ERROR", "MARKDOWN_DRIFT"),
    )


def _broken_format(
    testcase_id: str,
    block_text: str,
) -> tuple[str, FaultInjection]:
    matches = list(DATA_PATTERN.finditer(block_text))
    if len(matches) != 1:
        raise FaultInjectionError("Target block must contain exactly one machine-data comment.")
    match = matches[0]
    machine_json = match.group("data")
    broken_json, substitutions = re.subn(
        r'("format_version"\s*:\s*"[^"]+")(\s*,)',
        r"\1",
        machine_json,
        count=1,
    )
    if substitutions != 1:
        raise FaultInjectionError("Could not locate format_version delimiter to corrupt.")
    replacement = f"<!-- catalog:derived-data\n{broken_json}\n-->"
    rendered = block_text[: match.start()] + replacement + block_text[match.end() :]
    return rendered, FaultInjection(
        fault_class=FaultClass.BROKEN_FORMAT,
        testcase_id=testcase_id,
        changed_path=f"{testcase_id}.machine_data",
        original="valid-json",
        injected="missing-comma-after-format-version",
        expected_issue_codes=("DERIVED_DATA_INVALID", "MARKDOWN_DRIFT"),
    )


def _false_provenance(
    testcase_id: str,
    data: dict[str, Any],
    rules_path: Path,
) -> tuple[str, FaultInjection]:
    provenance = data["fields"]["timeout_seconds"]["provenance"]
    original = provenance["source_hash"]
    provenance["source_hash"] = "0" * 64 if original != "0" * 64 else "1" * 64
    return _render(testcase_id, data, rules_path), FaultInjection(
        fault_class=FaultClass.FALSE_PROVENANCE,
        testcase_id=testcase_id,
        changed_path=f"{testcase_id}.fields.timeout_seconds.provenance.source_hash",
        original=original,
        injected=provenance["source_hash"],
        expected_issue_codes=("FIELD_MISMATCH", "MARKDOWN_DRIFT"),
    )


def inject_fault(
    document: str,
    fault_class: FaultClass | str,
    testcase_id: str,
    rules_path: Path = DEFAULT_RULES_PATH,
) -> tuple[str, FaultInjection]:
    """Return a copy with exactly one deterministic fault in one derived block."""

    try:
        fault = FaultClass(fault_class)
    except ValueError as error:
        choices = ", ".join(item.value for item in FaultClass)
        raise FaultInjectionError(f"Unknown fault class; choose one of: {choices}") from error

    matching = [block for block in find_blocks(document) if block.testcase_id == testcase_id]
    if len(matching) != 1:
        raise FaultInjectionError(
            f"Expected exactly one derived block for {testcase_id}; found {len(matching)}."
        )
    block = matching[0]
    data = copy.deepcopy(parse_derived_block(block))

    if fault is FaultClass.WRONG_VALUE:
        rendered, metadata = _wrong_value(testcase_id, data, rules_path)
    elif fault is FaultClass.STALE_VALUE:
        rendered, metadata = _stale_value(testcase_id, data, rules_path)
    elif fault is FaultClass.HALLUCINATED_FIELD:
        rendered, metadata = _hallucinated_field(testcase_id, data, rules_path)
    elif fault is FaultClass.BROKEN_FORMAT:
        rendered, metadata = _broken_format(testcase_id, block.text)
    else:
        rendered, metadata = _false_provenance(testcase_id, data, rules_path)

    newline = "\r\n" if "\r\n" in document else "\n"
    rendered = rendered.replace("\n", newline)
    updated = document[: block.start] + rendered + document[block.end :]
    if updated == document:
        raise FaultInjectionError("Fault operator did not change the catalog.")
    return updated, metadata

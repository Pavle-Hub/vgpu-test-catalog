"""Versioned Markdown block format for deterministic catalog fields."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from vgpu_catalog.rules import CatalogRules

START_PATTERN = re.compile(r"<!-- catalog:derived:start (?P<testcase_id>TC-[0-9]{3}) -->")
END_PATTERN = re.compile(r"<!-- catalog:derived:end (?P<testcase_id>TC-[0-9]{3}) -->")
BLOCK_PATTERN = re.compile(
    r"<!-- catalog:derived:start (?P<testcase_id>TC-[0-9]{3}) -->"
    r".*?"
    r"<!-- catalog:derived:end (?P=testcase_id) -->",
    re.DOTALL,
)
DATA_PATTERN = re.compile(
    r"<!-- catalog:derived-data\r?\n(?P<data>.*?)\r?\n-->",
    re.DOTALL,
)


class CatalogBlockError(ValueError):
    """Raised when a machine-readable Markdown block is malformed."""


@dataclass(frozen=True, slots=True)
class CatalogBlock:
    testcase_id: str
    start: int
    end: int
    text: str


def _reject_nonstandard_number(value: str) -> None:
    raise ValueError(f"Non-standard JSON number is not allowed: {value}")


def normalize_newlines(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n")


def find_blocks(document: str) -> list[CatalogBlock]:
    return [
        CatalogBlock(
            testcase_id=match.group("testcase_id"),
            start=match.start(),
            end=match.end(),
            text=match.group(0),
        )
        for match in BLOCK_PATTERN.finditer(document)
    ]


def marker_ids(document: str) -> tuple[list[str], list[str]]:
    starts = [match.group("testcase_id") for match in START_PATTERN.finditer(document)]
    ends = [match.group("testcase_id") for match in END_PATTERN.finditer(document)]
    return starts, ends


def derived_block_data(testcase: dict[str, Any], rules: CatalogRules) -> dict[str, Any]:
    """Return only catalog fields, excluding internal aggregation evidence."""

    field_keys = {
        "supported_gpus": ("value", "status", "provenance"),
        "timeout_seconds": ("value", "status", "provenance"),
        "pass_rate_badge": ("value", "pass_rate_percent", "status", "provenance"),
        "last_measurement": ("value", "status", "provenance"),
    }
    fields = {
        field: {key: testcase[field][key] for key in keys} for field, keys in field_keys.items()
    }
    return {
        "format_version": rules.catalog.format_version,
        "testcase_id": testcase["testcase_id"],
        "fields": fields,
    }


def parse_derived_block(block: CatalogBlock) -> dict[str, Any]:
    matches = list(DATA_PATTERN.finditer(block.text))
    if len(matches) != 1:
        raise CatalogBlockError(
            f"{block.testcase_id} must contain exactly one catalog:derived-data comment."
        )

    try:
        value = json.loads(
            matches[0].group("data"),
            parse_constant=_reject_nonstandard_number,
        )
    except (json.JSONDecodeError, ValueError) as error:
        raise CatalogBlockError(f"Invalid derived JSON for {block.testcase_id}: {error}") from error

    if not isinstance(value, dict):
        raise CatalogBlockError(f"Derived data for {block.testcase_id} must be a JSON object.")
    return value


def _format_supported_gpus(values: list[str]) -> str:
    return ", ".join(f"`{gpu_id}`" for gpu_id in values) if values else "`none`"


def render_derived_block(testcase: dict[str, Any], rules: CatalogRules) -> str:
    """Render the exact visible and hidden representation checked by CI."""

    testcase_id = testcase["testcase_id"]
    timeout = testcase["timeout_seconds"]
    pass_rate = testcase["pass_rate_badge"]
    last_measurement = testcase["last_measurement"]

    timeout_text = (
        f"`{timeout['value']} s`" if timeout["value"] is not None else "`insufficient-data`"
    )
    if pass_rate["pass_rate_percent"] is None:
        pass_rate_text = "`insufficient-data`"
    else:
        rate = pass_rate["pass_rate_percent"]
        decimals = rules.pass_rate.decimal_places
        pass_rate_text = f"`{pass_rate['value']}` (`{rate:.{decimals}f}%`)"

    last_value = last_measurement["value"] or "no-measurement"
    machine_data = json.dumps(
        derived_block_data(testcase, rules),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )

    lines = [
        f"<!-- catalog:derived:start {testcase_id} -->",
        f"- **Supported GPUs:** {_format_supported_gpus(testcase['supported_gpus']['value'])}",
        f"- **Timeout:** {timeout_text}",
        f"- **Pass rate:** {pass_rate_text}",
        f"- **Last measurement:** `{last_value}` (`{last_measurement['status']}`)",
        "<!-- catalog:derived-data",
        machine_data,
        "-->",
        f"<!-- catalog:derived:end {testcase_id} -->",
    ]
    return "\n".join(lines)

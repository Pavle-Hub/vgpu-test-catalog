"""JSON Schema loading and validation shared by dataset components."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = PROJECT_ROOT / "schemas"

SCHEMA_FILES = {
    "runs": "runs.schema.json",
    "capabilities": "capabilities.schema.json",
    "manifest": "manifest.schema.json",
    "rules": "rules.schema.json",
    "catalog_derived": "catalog-derived.schema.json",
}


def load_schema(name: str) -> dict[str, Any]:
    try:
        filename = SCHEMA_FILES[name]
    except KeyError as error:
        raise ValueError(f"Unknown schema: {name}") from error

    return json.loads((SCHEMA_DIR / filename).read_text(encoding="utf-8"))


def iter_schema_errors(name: str, document: Any) -> list[str]:
    validator = Draft202012Validator(load_schema(name))
    messages: list[str] = []

    for error in sorted(validator.iter_errors(document), key=lambda item: list(item.path)):
        path = ".".join(str(part) for part in error.absolute_path) or "$"
        messages.append(f"{path}: {error.message}")

    return messages

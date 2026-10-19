"""Deterministic serialization and hashing helpers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def canonical_json_bytes(value: Any) -> bytes:
    """Serialize a value using the canonical form defined by ADR-005."""

    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def pretty_json_bytes(value: Any) -> bytes:
    """Serialize a repository artifact deterministically and readably."""

    text = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2)
    return f"{text}\n".encode()


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def artifact_record(path: Path) -> dict[str, str | int]:
    content = path.read_bytes()
    return {
        "path": path.name,
        "bytes": len(content),
        "sha256": sha256_bytes(content),
    }


def compute_snapshot_hash(artifacts: list[dict[str, str | int]]) -> str:
    ordered = sorted(artifacts, key=lambda artifact: str(artifact["path"]))
    return sha256_bytes(canonical_json_bytes(ordered))

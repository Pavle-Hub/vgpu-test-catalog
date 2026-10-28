"""Export three illustrative cases from saved evidence, without agent execution."""

from __future__ import annotations

import argparse
import difflib
import json
from pathlib import Path
from typing import Any

from vgpu_catalog.hashing import sha256_bytes
from vgpu_eval.codex_batch import ROOT, BatchError, write_json

EXAMPLES = (
    ("01-successful-repair", "ce1-hallucinated-field-r03-with-checker", "TC-003"),
    ("02-human-review", "ce1-broken-format-r02-with-checker", "TC-004"),
    ("03-clean-control", "ce1-clean-r02-with-checker", "TC-001"),
)


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def excerpt(data: bytes, testcase: str) -> bytes:
    text = data.decode("utf-8")
    marker = f"## {testcase}\n"
    start = text.index(marker)
    end = text.find("\n## TC-", start + len(marker))
    return text[start:end if end != -1 else None].encode("utf-8")


def difference(before: bytes, after: bytes, before_name: str, after_name: str) -> bytes:
    return "".join(difflib.unified_diff(
        before.decode("utf-8").splitlines(keepends=True),
        after.decode("utf-8").splitlines(keepends=True),
        fromfile=before_name, tofile=after_name,
    )).encode("utf-8")


def export_examples(source: Path, destination: Path) -> dict[str, Any]:
    source, destination = source.resolve(), destination.resolve()
    if destination.exists():
        raise BatchError("Example destination exists; refusing to overwrite it.")
    if destination.is_relative_to(source):
        raise BatchError("Export outside the original collection to preserve its contents.")
    revision = source / "reanalysis/audit-v2"
    correction = load(revision / "correction.json")
    frozen = load(source / "frozen-protocol.json")
    plan = load(source / "plan.json")
    if plan != frozen["identity"]["plan"]:
        raise BatchError("Plan differs from the frozen collection.")
    planned = {row["run_id"]: row for row in plan}
    payload: dict[str, bytes] = {}
    source_hashes: dict[str, str] = {}

    def read_evidence(relative: str) -> bytes:
        data = (source / relative).read_bytes()
        digest = sha256_bytes(data)
        expected = correction["source_sha256"].get(relative)
        if not relative.startswith("reanalysis/") and expected != digest:
            raise BatchError(f"Evidence differs from the audit-v2 record: {relative}")
        source_hashes[relative] = digest
        return data

    for name in ("frozen-protocol.json", "plan.json", "reanalysis/audit-v2/correction.json"):
        read_evidence(name)
    descriptions = []
    for label, run_id, testcase in EXAMPLES:
        relative = f"runs/{run_id}/attempt-01"
        raw = json.loads(read_evidence(f"{relative}/result.json"))
        revised = json.loads(read_evidence(f"reanalysis/audit-v2/{relative}/result.json"))
        audit = json.loads(read_evidence(f"reanalysis/audit-v2/{relative}/audit.json"))
        if run_id not in planned or any(raw.get(k) != v for k, v in planned[run_id].items()):
            raise BatchError(f"Example is not a planned final run: {run_id}")
        if raw["status"] != "completed" or revised["status"] != "completed":
            raise BatchError(f"Example must be completed: {run_id}")
        if revised["original_success"] != raw["success"]:
            raise BatchError(f"Revised/original score mismatch: {run_id}")
        if not revised["protected_fields_preserved"] or not revised["scope_preserved"]:
            raise BatchError(f"Example did not preserve protected boundaries: {run_id}")
        baseline = read_evidence(f"{relative}/baseline.md")
        before = read_evidence(f"{relative}/input.md")
        after = read_evidence(f"{relative}/agent-output.md")
        if (sha256_bytes(baseline) != raw["baseline_sha256"]
                or sha256_bytes(after) != raw["output_sha256"]):
            raise BatchError(f"Catalog hash mismatch: {run_id}")
        if label == "01-successful-repair" and not (
            revised["success"] and before != after and baseline == after
        ):
            raise BatchError("Successful-repair example does not satisfy its selection rule.")
        if label == "02-human-review" and not (
            not revised["success"] and not revised["checker_valid"]
            and revised["human_review_reported"] and before == after
            and revised["checker_attempts"] == 0
        ):
            raise BatchError("Human-review example does not satisfy its selection rule.")
        if label == "03-clean-control" and not (
            revised["condition"] == "clean" and revised["success"] and baseline == before == after
        ):
            raise BatchError("Clean-control example does not satisfy its selection rule.")
        for name, data in (("baseline.md", baseline), ("input.md", before), ("output.md", after)):
            payload[f"{label}/{name}"] = data
        payload[f"{label}/input-excerpt.md"] = excerpt(before, testcase)
        payload[f"{label}/output-excerpt.md"] = excerpt(after, testcase)
        payload[f"{label}/injection.diff"] = difference(baseline, before, "baseline.md", "input.md")
        payload[f"{label}/repair.diff"] = difference(before, after, "input.md", "output.md")
        payload[f"{label}/agent-final.txt"] = read_evidence(f"{relative}/agent-final.txt")
        payload[f"{label}/original-result.json"] = read_evidence(f"{relative}/result.json")
        payload[f"{label}/corrected-result.json"] = read_evidence(
            f"reanalysis/audit-v2/{relative}/result.json"
        )
        for name in ("initial-checker.json", "final-checker.json"):
            report = json.loads(read_evidence(f"{relative}/{name}"))
            # Keep issue content and validity, but replace workstation-specific paths.
            report["catalog_path"] = "catalog/test_catalog.md"
            report["dataset_dir"] = "dataset"
            payload[f"{label}/{name}"] = (
                json.dumps(report, ensure_ascii=False, indent=2) + "\n"
            ).encode("utf-8")
        audit_summary = {key: audit[key] for key in (
            "turn_completed", "checker_attempts", "evidence_read", "violations", "audit_limit"
        )}
        audit_summary["mcp_calls"] = {
            f"{server}/{tool}": sum(
                call["server"] == server and call["tool"] == tool
                and call["status"] == "completed" and not call["error"]
                for call in audit["mcp_calls"]
            )
            for server, tool in sorted({(c["server"], c["tool"]) for c in audit["mcp_calls"]})
        }
        payload[f"{label}/audit-summary.json"] = (
            json.dumps(audit_summary, ensure_ascii=False, indent=2) + "\n"
        ).encode("utf-8")
        descriptions.append({
            "category": label, "run_id": run_id, "attempt": "attempt-01",
            "excerpt_testcase": testcase, "success": revised["success"],
            "initial_valid": load(source / relative / "initial-checker.json")["valid"],
            "final_valid": revised["checker_valid"],
            "checker_attempts": revised["checker_attempts"],
            "input_sha256": sha256_bytes(before), "output_sha256": sha256_bytes(after),
        })
    manifest = {
        "protocol_id": frozen["identity"]["config"]["protocol_id"],
        "collection_head": frozen["identity"]["head"],
        "agent": frozen["identity"]["config"]["agent"],
        "source_collection": "eval/results/codex-eval-1",
        "source_scores": "reanalysis/audit-v2", "examples": descriptions,
        "selection_note": (
            "Illustrative, hand-selected completed final sessions, not an additional sample "
            "or evidence of outcome frequencies. All three use with-checker."
        ),
        "transformations": [
            "Checker report catalog_path/dataset_dir replaced with portable relative paths.",
            "Excerpts, diffs and audit summaries derived from preserved raw evidence.",
            "Full catalog snapshots, final messages and result JSON copied byte-for-byte.",
            "Runtime, credentials, shell commands and full event logs are not exported.",
        ],
        "source_sha256": source_hashes,
        "export_sha256": {name: sha256_bytes(data) for name, data in payload.items()},
    }
    # Validate the entire selection before creating output, and never mutate raw evidence.
    destination.mkdir(parents=True, exist_ok=False)
    for name, data in payload.items():
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    write_json(destination / "manifest.json", manifest)
    for name, digest in source_hashes.items():
        if sha256_bytes((source / name).read_bytes()) != digest:
            raise BatchError(f"Source changed during export: {name}")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "eval/results/codex-eval-1")
    parser.add_argument("--destination", type=Path, default=ROOT / "docs/evidence/examples-v1")
    args = parser.parse_args()
    try:
        manifest = export_examples(args.source, args.destination)
        print(json.dumps({"destination": str(args.destination), "examples": manifest["examples"]}))
        return 0
    except (OSError, ValueError, KeyError) as error:
        print(f"Example export stopped: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

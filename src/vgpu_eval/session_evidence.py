"""Export portable session details from preserved evidence; never invoke an agent."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from vgpu_catalog.hashing import sha256_bytes
from vgpu_eval.codex_batch import ROOT, BatchError, analyze, write_json
from vgpu_eval.examples import difference, excerpt


def export(source: Path, destination: Path) -> dict:
    source = source.resolve()
    if destination.exists():
        raise BatchError("Destination exists; refusing to overwrite evidence.")
    if destination.resolve().is_relative_to(source):
        raise BatchError("Export must be outside original collection.")
    correction = json.loads((source / "reanalysis/audit-v2/correction.json").read_bytes())
    hashes = {}

    def read(relative: str) -> bytes:
        path = (source / relative).resolve()
        if not path.is_relative_to(source):
            raise BatchError("Source path outside collection.")
        raw = path.read_bytes()
        digest = sha256_bytes(raw)
        if (not relative.startswith("reanalysis/")
                and correction["source_sha256"].get(relative) != digest):
            raise BatchError(f"Original evidence mismatch: {relative}")
        hashes[relative] = digest
        return raw

    plan = json.loads(read("plan.json"))
    frozen = json.loads(read("frozen-protocol.json"))
    read("reanalysis/audit-v2/correction.json")
    if frozen["identity"]["plan"] != plan:
        raise BatchError("Plan mismatch.")
    planned = {r["run_id"]: r for r in plan}
    sessions, attempts = {}, []
    for path in sorted((source / "reanalysis/audit-v2/runs").glob("*/*/result.json")):
        revised = json.loads(read(path.relative_to(source).as_posix()))
        attempts.append(revised)
        if revised["status"] != "completed":
            continue
        run_id = revised["run_id"]
        if run_id not in planned or any(revised[k] != v for k, v in planned[run_id].items()):
            raise BatchError("Run does not match frozen plan.")
        if run_id in sessions:
            raise BatchError("Duplicate completed run.")
        relative = f"runs/{run_id}/{path.parent.name}"
        raw_result = json.loads(read(f"{relative}/result.json"))
        before, after, baseline = (read(f"{relative}/{name}") for name in (
            "input.md", "agent-output.md", "baseline.md"
        ))
        if (sha256_bytes(after) != revised["output_sha256"]
                or sha256_bytes(baseline) != revised["baseline_sha256"]
                or raw_result["success"] != revised["original_success"]):
            raise BatchError("Saved catalog/result mismatch.")
        testcase = revised["testcase_id"] or "TC-001"
        reports = {}
        for name in ("initial-checker.json", "final-checker.json"):
            report = json.loads(read(f"{relative}/{name}"))
            report["catalog_path"], report["dataset_dir"] = "catalog/test_catalog.md", "dataset"
            reports[name] = report
        if reports["final-checker.json"]["valid"] != revised["checker_valid"]:
            raise BatchError("Final checker report differs from score.")
        sessions[run_id] = {
            "result": {k: v for k, v in revised.items() if k != "usage"},
            "excerpt_testcase": testcase,
            "input_excerpt": excerpt(before, testcase).decode(),
            "output_excerpt": excerpt(after, testcase).decode(),
            "repair_diff": difference(before, after, "input.md", "output.md").decode(),
            "reports": reports, "input_sha256": sha256_bytes(before),
        }
    summary = analyze(attempts, len(plan))
    if not summary["complete"] or summary != json.loads(read("reanalysis/audit-v2/summary.json")):
        raise BatchError("Corrected aggregate mismatch or incomplete collection.")
    payload = {"revision": "audit-v2", "collection_head": frozen["identity"]["head"],
               "summary": summary, "sessions": sessions}
    destination.mkdir(parents=True, exist_ok=False)
    write_json(destination / "sessions.json", payload)
    write_json(destination / "manifest.json", {
        "generator_sha256": sha256_bytes(Path(__file__).read_bytes()),
        "source_sha256": hashes,
        "files_sha256": {
            "sessions.json": sha256_bytes((destination / "sessions.json").read_bytes())
        },
        "notes": ["Target excerpts only; clean controls show TC-001, not the entire catalog.",
                  "Diff and hashes concern entire catalogs. Checker paths normalized.",
                  "Originals untouched; no agents invoked; interrupted attempts unscored."],
    })
    for relative, digest in hashes.items():
        if sha256_bytes((source / relative).read_bytes()) != digest:
            raise BatchError("Source changed during export.")
    return payload


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, default=ROOT / "eval/results/codex-eval-1")
    p.add_argument("--destination", type=Path, default=ROOT / "docs/evidence/sessions-v1")
    args = p.parse_args()
    try:
        data = export(args.source, args.destination)
        print(f"Exported {len(data['sessions'])} completed sessions; originals unchanged.")
        return 0
    except (OSError, ValueError, KeyError) as error:
        print(f"Export stopped: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

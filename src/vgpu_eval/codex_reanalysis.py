"""Offline, non-destructive audit correction of already collected experiments."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from vgpu_catalog.hashing import sha256_bytes
from vgpu_eval.codex_batch import (
    ROOT,
    BatchError,
    analyze,
    audit_events,
    now,
    read_events,
    write_analysis,
    write_json,
)


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def reanalyze(source: Path, destination: Path) -> dict[str, Any]:
    """Keep all raw evidence and original scores intact; write a separate revision."""
    source, destination = source.resolve(), destination.resolve()
    if destination.exists():
        raise BatchError("Reanalysis destination already exists; refusing to overwrite it.")
    if destination == source or destination.is_relative_to(source / "runs"):
        raise BatchError("Reanalysis must not be written into original run directories.")
    frozen = load(source / "frozen-protocol.json")
    plan = load(source / "plan.json")
    if frozen["identity"]["plan"] != plan:
        raise BatchError("Saved plan differs from frozen protocol.")
    original_results, corrected, changes, hashes = [], [], [], {}

    def record(path: Path) -> None:
        hashes[path.relative_to(source).as_posix()] = sha256_bytes(path.read_bytes())

    for name in ("frozen-protocol.json", "plan.json", "summary.json", "results.csv", "report.md"):
        record(source / name)
    for path in sorted((source / "runs").glob("*/*/result.json")):
        directory = path.parent
        result = load(path)
        original_results.append(result)
        # Hash all top-level raw evidence, but do not copy or modify workspaces.
        for evidence in sorted(directory.iterdir()):
            if evidence.is_file():
                record(evidence)
        for name, key in (("baseline.md", "baseline_sha256"), ("agent-output.md", "output_sha256")):
            if sha256_bytes((directory / name).read_bytes()) != result[key]:
                raise BatchError(f"Saved artifact hash mismatch: {directory / name}")
        if load(directory / "final-checker.json")["valid"] != result["checker_valid"]:
            raise BatchError(f"Saved checker result mismatch: {directory}")
        old_audit = load(directory / "audit.json")
        audit = audit_events(read_events(directory / "events.jsonl"), result["mode"])
        for key in ("checker_attempts", "evidence_read", "violations", "usage"):
            if old_audit[key] != result[key]:
                raise BatchError(f"Original audit/result mismatch for {key}: {directory}")
            if key != "violations" and audit[key] != result[key]:
                raise BatchError(f"Unexpected non-exclusion scoring change for {key}: {directory}")
        removed = set(result["violations"]) - set(audit["violations"])
        added = set(audit["violations"]) - set(result["violations"])
        if added or removed - {"direct-source-data-read"}:
            raise BatchError(f"Unexpected audit correction: {directory}")
        success = (
            result["status"] == "completed"
            and result["checker_valid"]
            and result["protected_fields_preserved"]
            and result["scope_preserved"]
            and not audit["violations"]
        )
        final = directory / "agent-final.txt"
        final_text = final.read_text(encoding="utf-8", errors="replace") if final.is_file() else ""
        revised = {
            **result,
            "success": success,
            "violations": audit["violations"],
            "original_success": result["success"],
            "original_violations": result["violations"],
            "human_review_reported": "human review" in final_text.lower(),
        }
        corrected.append((directory.relative_to(source), revised, audit))
        if removed or success != result["success"]:
            changes.append({
                "attempt": directory.relative_to(source).as_posix(),
                "run_id": result["run_id"],
                "old_success": result["success"],
                "new_success": success,
                "removed_violations": sorted(removed),
                "excluded_path_evidence": audit["source_path_exclusions"],
            })
    if analyze(original_results, len(plan)) != load(source / "summary.json"):
        raise BatchError("Original aggregate is not reproducible from saved results.")

    # No output is written until evidence validation has completed.
    destination.mkdir(parents=True, exist_ok=False)
    for relative, revised, audit in corrected:
        write_json(destination / relative / "result.json", revised)
        write_json(destination / relative / "audit.json", audit)
    summary = write_analysis(destination, plan)
    artifact_results = [
        {**result, "success": result["checker_valid"]
         and result["protected_fields_preserved"] and result["scope_preserved"]}
        for _, result, _ in corrected
    ]
    write_json(destination / "artifact-outcomes.json", analyze(artifact_results, len(plan)))
    review_stops = [
        result["run_id"] for _, result, _ in corrected
        if result["status"] == "completed" and not result["success"]
        and result["human_review_reported"] and not result["checker_valid"]
        and not result["changed_paths"]
    ]
    write_json(destination / "correction.json", {
        "revision": "audit-v2", "created_at": now(),
        "source": str(source), "collection_head": frozen["identity"]["head"],
        "reason": "Original path regex mistook negative rg --files globs for source reads.",
        "scope": "Only explicit negative file-listing globs are exempted; criteria unchanged.",
        "no_agent_sessions_invoked": True, "changed_attempts": changes,
        "human_review_stops": review_stops,
        "source_sha256": hashes,
        "analysis_code_sha256": {
            name: sha256_bytes((ROOT / "src/vgpu_eval" / name).read_bytes())
            for name in ("codex_batch.py", "codex_reanalysis.py")
        },
    })
    # Confirm that reanalysis did not touch any original evidence.
    for relative, digest in hashes.items():
        if sha256_bytes((source / relative).read_bytes()) != digest:
            raise BatchError(f"Original evidence changed during reanalysis: {relative}")
    lines = [
        "", "## Post-hoc audit correction", "",
        "Original scores and raw evidence remain unchanged in the collection directory.",
        f"Corrected attempts: {len(changes)}. No new agent sessions were invoked.",
        "The correction removes false source-read flags for explicit negative rg --files globs.",
        "Full changes, original evidence hashes, and analysis code hashes: correction.json.",
        "", "## Human-review stops and interpretation", "",
        f"Unrepaired, unchanged catalogs with explicit human-review reports: {len(review_stops)}.",
        "These remain failures of autonomous repair under the original success criteria.",
        "They must not automatically be interpreted as unsafe behavior or checker-caused errors.",
        "The frozen skill requests human review for structural errors; no skill was changed.",
        "Artifact validity is reported separately in artifact-outcomes.json, not substituted",
        "for full protocol compliance. Clean-control failures must not be called corruption",
        "without inspecting actual artifact changes.",
        "", "The observed mode difference does not establish general superiority or causality.",
    ]
    with (destination / "report.md").open("a", encoding="utf-8") as stream:
        stream.write("\n".join(lines) + "\n")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "eval/results/codex-eval-1")
    parser.add_argument("--destination", type=Path)
    args = parser.parse_args()
    destination = args.destination or args.source / "reanalysis/audit-v2"
    try:
        print(json.dumps(reanalyze(args.source, destination), indent=2))
        return 0
    except (OSError, ValueError, KeyError) as error:
        print(f"Reanalysis stopped: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

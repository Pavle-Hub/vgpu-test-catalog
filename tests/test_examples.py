import json
from pathlib import Path

import pytest

from vgpu_catalog.hashing import sha256_bytes
from vgpu_eval.codex_batch import ROOT, BatchError, write_json
from vgpu_eval.examples import EXAMPLES, difference, excerpt, export_examples


def example_source(source: Path) -> None:
    plan = []
    for label, run_id, testcase in EXAMPLES:
        relative = Path("runs") / run_id / "attempt-01"
        directory = source / relative
        directory.mkdir(parents=True)
        baseline = f"## {testcase}\n\nValid catalog.\n".encode()
        clean = label == "03-clean-control"
        review = label == "02-human-review"
        before = baseline if clean else baseline + b"Invalid field.\n"
        after = before if review else baseline
        row = {"run_id": run_id, "mode": "with-checker"}
        plan.append(row)
        result = {
            **row, "status": "completed", "success": not review,
            "checker_valid": not review, "condition": "clean" if clean else "fault",
            "protected_fields_preserved": True, "scope_preserved": True,
            "baseline_sha256": sha256_bytes(baseline), "output_sha256": sha256_bytes(after),
            "checker_attempts": 0 if review else 1,
        }
        for name, data in (("baseline.md", baseline), ("input.md", before),
                           ("agent-output.md", after), ("agent-final.txt", b"Final report.")):
            (directory / name).write_bytes(data)
        write_json(directory / "result.json", result)
        for name, valid in (("initial-checker.json", clean), ("final-checker.json", not review)):
            write_json(directory / name, {
                "valid": valid, "issues": [], "catalog_path": "private/path/catalog.md",
                "dataset_dir": "private/path/dataset",
            })
        revised = {**result, "original_success": result["success"], "human_review_reported": review}
        revision = source / "reanalysis/audit-v2" / relative
        write_json(revision / "result.json", revised)
        write_json(revision / "audit.json", {
            "turn_completed": True, "checker_attempts": result["checker_attempts"],
            "evidence_read": not review, "violations": [], "audit_limit": "Text audit.",
            "mcp_calls": [],
        })
    write_json(source / "plan.json", plan)
    write_json(source / "frozen-protocol.json", {"identity": {
        "plan": plan, "head": "original-collection", "config": {
            "protocol_id": "test-protocol", "agent": {"model": "test-model"},
        },
    }})
    hashes = {
        p.relative_to(source).as_posix(): sha256_bytes(p.read_bytes())
        for p in source.rglob("*") if p.is_file() and "reanalysis" not in p.parts
    }
    write_json(source / "reanalysis/audit-v2/correction.json", {"source_sha256": hashes})


def test_export_is_offline_preserves_sources_and_normalizes_only_report_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    source, destination = tmp_path / "source", tmp_path / "export"
    example_source(source)
    before = {p: p.read_bytes() for p in source.rglob("*") if p.is_file()}
    monkeypatch.setattr(
        "subprocess.Popen", lambda *a, **kw: pytest.fail("Export must not run subprocesses")
    )
    manifest = export_examples(source, destination)
    assert len(manifest["examples"]) == 3
    assert all(p.read_bytes() == data for p, data in before.items())
    for relative, digest in manifest["export_sha256"].items():
        assert sha256_bytes((destination / relative).read_bytes()) == digest
    report = json.loads((destination / EXAMPLES[0][0] / "final-checker.json").read_text())
    assert report["catalog_path"] == "catalog/test_catalog.md"
    assert report["dataset_dir"] == "dataset"
    assert (destination / EXAMPLES[1][0] / "repair.diff").read_bytes() == b""
    assert (destination / EXAMPLES[2][0] / "repair.diff").read_bytes() == b""
    with pytest.raises(BatchError, match="exists"):
        export_examples(source, destination)


def test_export_refuses_changed_evidence(tmp_path: Path) -> None:
    source, destination = tmp_path / "source", tmp_path / "export"
    example_source(source)
    (source / "runs" / EXAMPLES[0][1] / "attempt-01/input.md").write_bytes(b"Changed")
    with pytest.raises(BatchError, match="differs from"):
        export_examples(source, destination)
    assert not destination.exists()


def test_committed_example_pack_matches_its_manifest() -> None:
    destination = ROOT / "docs/evidence/examples-v1"
    manifest = json.loads((destination / "manifest.json").read_text(encoding="utf-8"))
    for relative, digest in manifest["export_sha256"].items():
        assert sha256_bytes((destination / relative).read_bytes()) == digest


def test_excerpts_and_diffs_do_not_rewrite_full_snapshots() -> None:
    data = b"# Header\n\n## TC-001\nFirst\n\n## TC-002\nSecond\n"
    assert excerpt(data, "TC-001") == b"## TC-001\nFirst\n"
    assert difference(data, data, "before", "after") == b""

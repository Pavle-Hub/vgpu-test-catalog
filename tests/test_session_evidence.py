import json
import shutil
import subprocess
from pathlib import Path

import pytest

from vgpu_catalog.hashing import sha256_bytes
from vgpu_eval.codex_batch import ROOT, BatchError, analyze
from vgpu_eval.dashboard import snapshot
from vgpu_eval.session_evidence import export


def test_session_pack_matches_corrected_summary_and_hashes() -> None:
    pack = ROOT / "docs/evidence/sessions-v1"
    data = json.loads((pack / "sessions.json").read_bytes())
    manifest = json.loads((pack / "manifest.json").read_bytes())
    assert len(data["sessions"]) == 60
    summary = analyze([v["result"] for v in data["sessions"].values()], 60)
    assert summary["groups"] == data["summary"]["groups"]
    assert summary["paired"] == data["summary"]["paired"]
    assert data["summary"]["interrupted_attempts"] == 1
    for name, digest in manifest["files_sha256"].items():
        assert sha256_bytes((pack / name).read_bytes()) == digest
    assert b"C:\\\\Users" not in (pack / "sessions.json").read_bytes()


def test_export_refuses_existing_destination(tmp_path: Path) -> None:
    with pytest.raises(BatchError, match="exists"):
        export(tmp_path / "missing", tmp_path)


def test_export_rejects_original_hash_mismatch_before_writing(tmp_path: Path) -> None:
    source = tmp_path / "source"
    correction = source / "reanalysis/audit-v2/correction.json"
    correction.parent.mkdir(parents=True)
    correction.write_text(json.dumps({"source_sha256": {"plan.json": "wrong"}}))
    (source / "plan.json").write_text("[]")
    destination = tmp_path / "export"
    with pytest.raises(BatchError, match="mismatch"):
        export(source, destination)
    assert not destination.exists()


def test_frontend_interactions_with_node(tmp_path: Path) -> None:
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is optional; required to execute frontend contract tests")
    fixture = tmp_path / "data.json"
    fixture.write_text(json.dumps(snapshot()), encoding="utf-8")
    result = subprocess.run(
        [node, str(ROOT / "tests/dashboard_interactions.cjs"), str(fixture)],
        capture_output=True, text=True, timeout=30, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "contracts passed" in result.stdout

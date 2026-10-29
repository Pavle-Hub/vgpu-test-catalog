import shutil
from pathlib import Path

import pytest

from vgpu_eval.readiness import ROOT, inspect


def test_preflight_is_offline_and_does_not_modify_evidence(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("subprocess.Popen", lambda *a, **kw: pytest.fail("No processes expected"))
    evidence = ROOT / "docs/evidence/sessions-v1/sessions.json"
    before = evidence.read_bytes()
    report = inspect()
    assert report["ready"]
    assert {c["name"] for c in report["checks"]} >= {"dataset", "catalog", "dashboard"}
    assert evidence.read_bytes() == before


def test_missing_node_is_warning_not_demo_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("vgpu_eval.readiness.shutil.which", lambda _: None)
    report = inspect()
    assert report["ready"]
    assert next(c for c in report["checks"] if c["name"] == "node-tests")["status"] == "warn"


def test_missing_dashboard_asset_blocks_demo(tmp_path: Path) -> None:
    for directory in ("dataset", "catalog", "docs/evidence"):
        shutil.copytree(ROOT / directory, tmp_path / directory)
    shutil.copyfile(ROOT / "rules.yaml", tmp_path / "rules.yaml")
    shutil.copyfile(ROOT / "requirements.lock", tmp_path / "requirements.lock")
    report = inspect(tmp_path)
    assert not report["ready"]
    assert next(c for c in report["checks"] if c["name"] == "dashboard")["status"] == "fail"

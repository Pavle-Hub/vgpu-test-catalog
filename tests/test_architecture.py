import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from vgpu_catalog.hashing import sha256_bytes
from vgpu_eval.architecture import REFERENCES, build, evaluation, maintenance
from vgpu_eval.codex_batch import ROOT, BatchError
from vgpu_eval.results_figures import svg

PACK = ROOT / "docs/evidence/architecture-v1"


@pytest.mark.parametrize("factory", [maintenance, evaluation])
def test_all_edges_reference_present_nodes_and_fit_canvas(factory) -> None:
    diagram = factory()
    for edge in diagram.edges:
        assert edge["source"] in diagram.nodes
        assert edge["target"] in diagram.nodes
    for shape in diagram.drawing["shapes"]:
        assert 0 <= shape["x"] < diagram.drawing["width"]
        assert 0 <= shape["y"] < diagram.drawing["height"]
    document = ET.fromstring(svg(diagram.drawing))
    namespace = {"s": "http://www.w3.org/2000/svg"}
    assert document.find("s:title", namespace).text == diagram.drawing["title"]
    assert "flowchart LR" in diagram.mermaid()


def test_agent_feedback_is_explicitly_conditional_and_ci_is_separate() -> None:
    diagram = maintenance()
    feedback = [e for e in diagram.edges if e["conditional"]]
    assert len(feedback) == 1
    assert feedback[0]["source"] == "checker" and feedback[0]["target"] == "agent"
    assert "samo with-checker" in feedback[0]["label"]
    assert not any(e["source"] == "snapshot" and e["target"] == "agent" for e in diagram.edges)
    assert not any(e["source"] == "mcp" and e["target"] == "checker" for e in diagram.edges)
    experiment_nodes = {"plan", "workspace", "session", "score", "raw", "analysis"}
    ci_nodes = {"pr", "gate", "ruleset", "merge"}
    for edge in evaluation().edges:
        assert ({edge["source"], edge["target"]} <= experiment_nodes
                or {edge["source"], edge["target"]} <= ci_nodes)


def test_reference_paths_exist_and_cover_core_modules() -> None:
    for paths in REFERENCES.values():
        assert all((ROOT / path).is_file() for path in paths)
    assert "src/catalog_check/checker.py" in REFERENCES["checker"]
    assert ".github/workflows/catalog-ci.yml" in REFERENCES["ci"]


def test_build_is_offline_deterministic_and_does_not_overwrite(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("vgpu_eval.architecture.git", lambda *args: "test-head")
    monkeypatch.setattr(
        "subprocess.Popen", lambda *args, **kwargs: pytest.fail("No live process is required")
    )
    destination = tmp_path / "architecture"
    build(destination)
    assert (destination / "maintenance.svg").read_bytes() == (PACK / "maintenance.svg").read_bytes()
    assert (destination / "evaluation-and-ci.mmd").read_bytes() == (
        PACK / "evaluation-and-ci.mmd"
    ).read_bytes()
    with pytest.raises(BatchError, match="exists"):
        build(destination)


def test_pack_integrity_and_no_personal_paths() -> None:
    manifest = json.loads((PACK / "manifest.json").read_text())
    for name, digest in manifest["files_sha256"].items():
        assert sha256_bytes((PACK / name).read_bytes()) == digest
    assert not any("C:" in path or "Users" in path for path in manifest["source_sha256"])

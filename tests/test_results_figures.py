import copy
import json
import struct
import sys
import xml.etree.ElementTree as ET
import zlib
from pathlib import Path

import pytest

from vgpu_catalog.hashing import sha256_bytes
from vgpu_eval.codex_batch import ROOT, BatchError, analyze
from vgpu_eval.png_render import png_bytes, render
from vgpu_eval.results_figures import build, chart, collect_data, svg, tables

PACK = ROOT / "docs/evidence/results-v1"


def data() -> dict:
    return json.loads((PACK / "data.json").read_text(encoding="utf-8"))


def test_portable_attempts_reproduce_corrected_complete_summary() -> None:
    bundle = data()
    summary = analyze(bundle["attempts"], 60)
    assert summary == bundle["summary"]
    assert summary["completed_runs"] == 60
    assert summary["interrupted_attempts"] == 1
    assert summary["groups"]["fault/with-checker"]["successes"] == 21
    assert summary["groups"]["fault/without-checker"]["successes"] == 25
    assert summary["paired"]["fault"]["exact_p_two_sided"] == 0.125


def test_tables_keep_controls_separate_and_use_corrected_scores() -> None:
    content = tables(data()["summary"])
    assert "21/25 (84,0%)" in content
    assert "25/25 (100,0%)" in content
    assert "5/5 (100,0%)" in content
    assert "20/25" not in content
    assert "Kontrole bez ubačene greške" in content
    assert "0,125" in content


@pytest.mark.parametrize("by_class,points", [(True, 12), (False, 6)])
def test_chart_has_expected_markers_and_parseable_vector_output(
    by_class: bool, points: int,
) -> None:
    drawing = chart(data()["summary"], by_class=by_class)
    assert sum(s["type"] == "point" for s in drawing["shapes"]) == points
    document = ET.fromstring(svg(drawing))
    assert document.tag.endswith("svg")
    for shape in drawing["shapes"]:
        assert 0 <= shape["x"] <= drawing["width"]
        assert 0 <= shape["y"] <= drawing["height"]


def test_build_is_offline_and_refuses_overwrite_or_inconsistent_data(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "subprocess.Popen", lambda *a, **kw: pytest.fail("No subprocess or model required")
    )
    bundle = data()
    destination = tmp_path / "results"
    build(bundle, destination)
    assert (destination / "tables.md").read_bytes() == (PACK / "tables.md").read_bytes()
    assert (destination / "by-class.svg").read_bytes() == (PACK / "by-class.svg").read_bytes()
    with pytest.raises(BatchError, match="exists"):
        build(bundle, destination)
    bad = copy.deepcopy(bundle)
    bad["attempts"][0]["success"] = not bad["attempts"][0]["success"]
    with pytest.raises(BatchError, match="reproduce"):
        build(bad, tmp_path / "bad")
    assert not (tmp_path / "bad").exists()


def test_collect_refuses_mismatched_frozen_plan(tmp_path: Path) -> None:
    source = tmp_path / "collection/reanalysis/audit-v2"
    source.mkdir(parents=True)
    collection = source.parent.parent
    (collection / "plan.json").write_text("[]")
    (collection / "frozen-protocol.json").write_text(json.dumps({"identity": {
        "plan": [{"run_id": "unexpected"}], "head": "test",
    }}))
    (source / "correction.json").write_text(json.dumps({"collection_head": "test"}))
    with pytest.raises(BatchError, match="Plan differs"):
        collect_data(source)


def test_committed_figure_pack_hashes_match_manifest() -> None:
    manifest = json.loads((PACK / "manifest.json").read_text())
    for name, digest in manifest["files_sha256"].items():
        assert sha256_bytes((PACK / name).read_bytes()) == digest


def test_png_encoder_round_trip_and_checksum() -> None:
    encoded = png_bytes(2, 1, b"\xff\x00\x00\x00\xff\x00")
    assert encoded[:8] == b"\x89PNG\r\n\x1a\n"
    offset, compressed = 8, b""
    while offset < len(encoded):
        size = struct.unpack(">I", encoded[offset:offset + 4])[0]
        kind = encoded[offset + 4:offset + 8]
        content = encoded[offset + 8:offset + 8 + size]
        crc = struct.unpack(">I", encoded[offset + 8 + size:offset + 12 + size])[0]
        assert crc == zlib.crc32(kind + content)
        if kind == b"IDAT":
            compressed += content
        offset += size + 12
    assert zlib.decompress(compressed) == b"\x00\xff\x00\x00\x00\xff\x00"
    with pytest.raises(ValueError, match="buffer"):
        png_bytes(2, 1, b"short")


@pytest.mark.skipif(sys.platform != "win32", reason="Windows GDI renderer")
def test_windows_raster_renderer_creates_2x_png(tmp_path: Path) -> None:
    destination = tmp_path / "point.png"
    render({"width": 40, "height": 30, "shapes": [
        {"type": "point", "x": 20, "y": 15, "color": "#2366A8", "square": False},
    ]}, destination)
    content = destination.read_bytes()
    assert struct.unpack(">II", content[16:24]) == (80, 60)
    with pytest.raises(FileExistsError):
        render({}, destination)

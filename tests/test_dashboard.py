import io
import json
from pathlib import Path

import pytest

from vgpu_eval.codex_batch import ROOT
from vgpu_eval.dashboard import ASSETS, CASES, catalog_records, handler, read, snapshot, verify_pack


@pytest.fixture(scope="module")
def data() -> dict:
    return snapshot()


def request(data: dict, route: str, method: str = "GET", host: str = "127.0.0.1:8765"):
    cls = handler(ROOT, data)
    instance = cls.__new__(cls)
    instance.client_address = ("127.0.0.1", 12345)
    instance.rfile = io.BytesIO(
        f"{method} {route} HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n".encode()
    )
    instance.wfile = io.BytesIO()
    instance.log_message = lambda *args: None
    instance.close_connection = True
    instance.handle_one_request()
    headers, body = instance.wfile.getvalue().split(b"\r\n\r\n", 1)
    return headers.decode(), body


def test_snapshot_contains_only_intended_saved_evidence(data: dict) -> None:
    assert len(data["catalog"]) == 10
    assert set(data["cases"]) == set(CASES)
    assert data["summary"]["completed_runs"] == 60
    assert data["summary"]["groups"]["fault/with-checker"]["successes"] == 21
    assert data["summary"]["groups"]["fault/without-checker"]["successes"] == 25
    assert data["revision"] == "audit-v2"
    assert data["catalog"][2]["testcase_id"] == "TC-003"
    assert "Validate the advanced" in data["catalog"][2]["prose"]["Purpose"]
    assert data["cases"][CASES[1]]["corrected-result.json"]["checker_valid"] is False


@pytest.mark.parametrize("route", [
    "/", "/app.js", "/style.css", "/api/data", "/figures/overall.svg",
])
def test_allowlisted_routes_return_content_and_security_headers(data: dict, route: str) -> None:
    headers, body = request(data, route)
    assert "200 OK" in headers
    assert "Content-Security-Policy:" in headers
    assert "nosniff" in headers
    assert "no-store" in headers
    assert body
    if route == "/api/data":
        assert json.loads(body)["summary"] == data["summary"]


@pytest.mark.parametrize("route", [
    "/../.codex/config.toml", "/%2e%2e/.git/config", "/dataset/runs.json",
    "/eval/results/", "/api/run", "/api/data/../../README.md", "/.env",
])
def test_other_paths_are_not_served(data: dict, route: str) -> None:
    assert "404" in request(data, route)[0]


@pytest.mark.parametrize("method", ["POST", "PUT", "DELETE", "PATCH"])
def test_mutating_http_methods_are_not_implemented(data: dict, method: str) -> None:
    assert "501" in request(data, "/api/data", method)[0]


def test_head_has_no_body_and_foreign_host_is_rejected(data: dict) -> None:
    headers, body = request(data, "/api/data", "HEAD")
    assert "200 OK" in headers and body == b""
    assert "403" in request(data, "/api/data", host="evil.example")[0]


def test_read_rejects_paths_outside_project(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    (tmp_path / "secret.txt").write_text("not exposed")
    with pytest.raises(ValueError, match="outside"):
        read(root, "../secret.txt")


def test_evidence_hash_mismatch_stops_loading(tmp_path: Path) -> None:
    pack = tmp_path / "pack"
    pack.mkdir()
    (pack / "manifest.json").write_text(json.dumps({"files": {"sample.json": "wrong"}}))
    (pack / "sample.json").write_text("{}")
    with pytest.raises(ValueError, match="hash mismatch"):
        verify_pack(tmp_path, "pack", "files")


def test_reading_dashboard_never_launches_processes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("subprocess.Popen", lambda *a, **kw: pytest.fail("Read-only dashboard"))
    assert snapshot()["notice"].startswith("Historical")


def test_frontend_assets_exist_and_do_not_use_html_injection() -> None:
    assert all((ROOT / value[0]).is_file() for value in ASSETS.values())
    script = (ROOT / "web/dashboard/app.js").read_text(encoding="utf-8")
    assert "innerHTML" not in script
    assert "textContent" in script
    assert "fetch('/api/data')" in script
    assert catalog_records("# Empty") == []

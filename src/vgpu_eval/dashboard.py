"""Loopback-only, read-only dashboard for committed thesis evidence."""

from __future__ import annotations

import argparse
import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from catalog_check.markdown import find_blocks, parse_derived_block
from vgpu_catalog.hashing import sha256_bytes
from vgpu_eval.codex_batch import ROOT, analyze

CASES = ("01-successful-repair", "02-human-review", "03-clean-control")
CASE_FILES = (
    "input.md", "output.md", "input-excerpt.md", "output-excerpt.md", "repair.diff",
    "injection.diff", "agent-final.txt", "initial-checker.json", "final-checker.json",
    "corrected-result.json", "audit-summary.json",
)
ASSETS = {
    "/": ("web/dashboard/index.html", "text/html; charset=utf-8"),
    "/app.js": ("web/dashboard/app.js", "text/javascript; charset=utf-8"),
    "/style.css": ("web/dashboard/style.css", "text/css; charset=utf-8"),
    "/figures/by-class.svg": ("docs/evidence/results-v1/by-class.svg", "image/svg+xml"),
    "/figures/overall.svg": ("docs/evidence/results-v1/overall-and-controls.svg", "image/svg+xml"),
    "/figures/maintenance.svg": ("docs/evidence/architecture-v1/maintenance.svg", "image/svg+xml"),
    "/figures/evaluation.svg": (
        "docs/evidence/architecture-v1/evaluation-and-ci.svg", "image/svg+xml"
    ),
}


def read(root: Path, relative: str) -> bytes:
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("Path outside dashboard source.")
    return path.read_bytes()


def load(root: Path, relative: str) -> Any:
    return json.loads(read(root, relative))


def verify_pack(root: Path, relative: str, key: str) -> None:
    manifest = load(root, f"{relative}/manifest.json")
    for name, digest in manifest[key].items():
        if sha256_bytes(read(root, f"{relative}/{name}")) != digest:
            raise ValueError(f"Evidence hash mismatch: {relative}/{name}")


def catalog_records(document: str) -> list[dict[str, Any]]:
    sections = dict(re.findall(r"^## (TC-\d+)\s*\n(.*?)(?=^## TC-|\Z)", document, re.M | re.S))
    records = []
    for block in find_blocks(document):
        data = parse_derived_block(block)
        prose = dict(re.findall(
            r"^### (Purpose|Notes|Summary)\s*\n(.*?)(?=^### |\Z)",
            sections[block.testcase_id], re.M | re.S,
        ))
        records.append({**data, "prose": {k: v.strip() for k, v in prose.items()}})
    return records


def snapshot(root: Path = ROOT) -> dict[str, Any]:
    verify_pack(root, "docs/evidence/examples-v1", "export_sha256")
    verify_pack(root, "docs/evidence/results-v1", "files_sha256")
    verify_pack(root, "docs/evidence/architecture-v1", "files_sha256")
    data = load(root, "docs/evidence/results-v1/data.json")
    if analyze(data["attempts"], data["summary"]["expected_runs"]) != data["summary"]:
        raise ValueError("Saved scores do not reproduce the summary.")
    cases = {}
    for case in CASES:
        case_data = {}
        for name in CASE_FILES:
            raw = read(root, f"docs/evidence/examples-v1/{case}/{name}")
            case_data[name] = json.loads(raw) if name.endswith(".json") else raw.decode("utf-8")
        cases[case] = case_data
    catalog = read(root, "catalog/test_catalog.md")
    return {
        "protocol": data["protocol_id"], "agent": data["agent"],
        "collection_head": data["collection_head"], "revision": data["score_revision"],
        "summary": data["summary"], "attempts": data["attempts"],
        "corrections": data["corrected_attempts"],
        "catalog": catalog_records(catalog.decode("utf-8")),
        "catalog_sha256": sha256_bytes(catalog),
        "source": load(root, "dataset/manifest.json"), "cases": cases,
        "notice": "Historical evidence replay; no new agent or checker execution.",
    }


def handler(root: Path, data: dict[str, Any]) -> type[BaseHTTPRequestHandler]:
    class DashboardHandler(BaseHTTPRequestHandler):
        server_version = "CatalogDashboard/1"
        sys_version = ""

        def do_GET(self) -> None:
            self.respond(False)

        def do_HEAD(self) -> None:
            self.respond(True)

        def respond(self, head: bool) -> None:
            try:
                host = urlsplit("http://" + self.headers.get("Host", "")).hostname
                if host not in {"127.0.0.1", "localhost"}:
                    self.send_error(403)
                    return
                route = urlsplit(self.path).path
                if route == "/api/data":
                    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
                    content_type = "application/json; charset=utf-8"
                elif route in ASSETS:
                    relative, content_type = ASSETS[route]
                    body = read(root, relative)
                else:
                    self.send_error(404)
                    return
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Referrer-Policy", "no-referrer")
                self.send_header(
                    "Content-Security-Policy", "default-src 'none'; script-src 'self'; "
                    "style-src 'self'; img-src 'self'; connect-src 'self'; "
                    "base-uri 'none'; frame-ancestors 'none'",
                )
                self.end_headers()
                if not head:
                    self.wfile.write(body)
            except (OSError, ValueError, KeyError):
                self.send_error(500, "Dashboard evidence unavailable")

    return DashboardHandler


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    try:
        data = snapshot()
        server = ThreadingHTTPServer(("127.0.0.1", args.port), handler(ROOT, data))
        print(f"Dashboard: http://127.0.0.1:{server.server_port} "
              "(read-only; Ctrl+C to stop)", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
        return 0
    except (OSError, ValueError, KeyError) as error:
        print(f"Dashboard stopped: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

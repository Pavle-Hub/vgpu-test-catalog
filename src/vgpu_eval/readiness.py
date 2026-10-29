"""Read-only local demo preflight: no network, agents, repairs, or new results."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import shutil
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]


def inspect(root: Path = ROOT) -> dict[str, Any]:
    checks = []

    def add(name: str, status: str, message: str) -> None:
        checks.append({"name": name, "status": status, "message": message})

    version = sys.version_info[:3]
    if not (3, 11) <= version[:2] < (3, 15):
        add("python", "fail", "Supported Python versions: 3.11 through 3.14.")
    else:
        add("python", "pass" if version == (3, 13, 16) else "warn",
            f"Python {'.'.join(map(str, version))}; reference environment: 3.13.16.")
    locked = {}
    for line in (root / "requirements.lock").read_text(encoding="utf-8").splitlines():
        if "==" in line and not line.startswith("#"):
            name, version_text = line.split("==", 1)
            locked[name.lower()] = version_text.strip()
    for name in ("mcp", "jsonschema", "PyYAML"):
        try:
            actual = importlib.metadata.version(name)
            expected = locked.get(name.lower())
            add(f"package/{name}", "pass" if actual == expected else "warn",
                f"Installed: {actual}; locked: {expected}.")
        except importlib.metadata.PackageNotFoundError:
            add(f"package/{name}", "fail", "Missing runtime package; install requirements.lock.")
    try:
        from vgpu_catalog.validation import validate_dataset

        report = validate_dataset(root / "dataset")
        add("dataset", "pass" if report.valid else "fail",
            f"Source validation issues: {len(report.issues)}.")
    except (ImportError, OSError, ValueError, KeyError) as error:
        add("dataset", "fail", f"Cannot validate source: {type(error).__name__}.")
    try:
        from catalog_check.checker import check_catalog

        report = check_catalog(
            root / "catalog/test_catalog.md", root / "dataset", root / "rules.yaml"
        )
        add("catalog", "pass" if report.valid else "fail",
            f"Read-only checker issues: {len(report.issues)}.")
    except (ImportError, OSError, ValueError, KeyError) as error:
        add("catalog", "fail", f"Cannot check catalog: {type(error).__name__}.")
    try:
        from vgpu_eval.dashboard import ASSETS, read, snapshot

        data = snapshot(root)
        for relative, _ in ASSETS.values():
            read(root, relative)
        add("dashboard", "pass", f"Evidence hashes and web assets verified; "
            f"{len(data['sessions'])} saved completed sessions.")
    except (ImportError, OSError, ValueError, KeyError) as error:
        add("dashboard", "fail", f"Cannot load evidence or assets: {type(error).__name__}.")
    add("node-tests", "pass" if shutil.which("node") else "warn",
        "Node found for optional frontend tests." if shutil.which("node")
        else "Node absent: dashboard still works; frontend contract test will be skipped.")
    return {"ready": not any(c["status"] == "fail" for c in checks), "checks": checks,
            "limits": ["Not a full pytest run or browser test.",
                       "Does not launch or validate live MCP/agent integration.",
                       "Does not contact GitHub or prove current branch-rule enforcement.",
                       "Current catalog check is not a new experimental session score."]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Print machine-readable results.")
    args = parser.parse_args()
    try:
        report = inspect()
    except (OSError, ValueError) as error:
        print(f"Preflight cannot read project inputs: {type(error).__name__}.")
        return 1
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        for check in report["checks"]:
            print(f"[{check['status'].upper()}] {check['name']}: {check['message']}")
        print("READY for local demo." if report["ready"] else "NOT READY: resolve FAIL entries.")
        print("Read-only check; no agents, network requests, or evidence writes.")
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

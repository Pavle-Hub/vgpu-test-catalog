"""Command-line interface for deterministic catalog verification."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from catalog_check.checker import (
    CatalogWriteError,
    check_catalog,
    report_json,
    write_catalog,
)
from vgpu_catalog.rules import DEFAULT_RULES_PATH


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="Verify without modifying files.")
    mode.add_argument("--write", action="store_true", help="Replace only derived blocks.")
    parser.add_argument("--catalog", type=Path, default=Path("catalog/test_catalog.md"))
    parser.add_argument("--dataset", type=Path, default=Path("dataset"))
    parser.add_argument("--rules", type=Path, default=DEFAULT_RULES_PATH)
    args = parser.parse_args()

    try:
        if args.write:
            report, changed = write_catalog(args.catalog, args.dataset, args.rules)
            print(report_json(report, mode="write", written=changed))
        else:
            report = check_catalog(args.catalog, args.dataset, args.rules)
            print(report_json(report, mode="check"))
    except (CatalogWriteError, OSError, ValueError) as error:
        print(
            json.dumps(
                {"mode": "write" if args.write else "check", "valid": False, "error": str(error)},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1

    return 0 if report.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())

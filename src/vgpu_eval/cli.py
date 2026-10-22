"""Command-line interface for deterministic checker and agent evaluation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from vgpu_catalog.hashing import pretty_json_bytes
from vgpu_catalog.rules import DEFAULT_RULES_PATH
from vgpu_eval.faults import FaultClass, FaultInjectionError
from vgpu_eval.runs import (
    AgentRunError,
    finish_agent_run,
    restore_agent_run,
    start_agent_run,
    summarize_agent_runs,
)
from vgpu_eval.suite import EvaluationSuiteError, generate_detection_suite

DEFAULT_CATALOG = Path("catalog/test_catalog.md")
DEFAULT_DATASET = Path("dataset")
DEFAULT_RESULTS = Path("eval/results/runs")


def _print(value: dict[str, Any]) -> None:
    print(pretty_json_bytes(value).decode("utf-8"), end="")


def _common_paths(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--rules", type=Path, default=DEFAULT_RULES_PATH)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    suite = subparsers.add_parser("suite", help="Generate checker detection cases and metrics.")
    _common_paths(suite)
    suite.add_argument("--output", type=Path, required=True)
    suite.add_argument("--testcase", action="append", dest="testcases")

    start = subparsers.add_parser("start", help="Inject one in-place agent experiment fault.")
    _common_paths(start)
    start.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS)
    start.add_argument("--fault-class", choices=[item.value for item in FaultClass], required=True)
    start.add_argument("--testcase", required=True)
    start.add_argument("--model", required=True)
    start.add_argument("--mode", choices=["with-checker", "without-checker"], required=True)
    start.add_argument("--run-id")
    start.add_argument("--prompt", type=Path)

    finish = subparsers.add_parser("finish", help="Record the current agent output.")
    _common_paths(finish)
    finish.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS)
    finish.add_argument("--run-id", required=True)
    finish.add_argument("--checker-attempts", type=int, required=True)
    finish.add_argument("--notes")

    restore = subparsers.add_parser("restore", help="Restore a recorded run baseline.")
    restore.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    restore.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS)
    restore.add_argument("--run-id", required=True)

    summarize = subparsers.add_parser("summarize", help="Aggregate recorded agent runs.")
    summarize.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS)
    summarize.add_argument("--output", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        display: dict[str, Any] | None = None
        if args.command == "suite":
            result = generate_detection_suite(
                args.catalog,
                args.dataset,
                args.output,
                rules_path=args.rules,
                selected_testcases=args.testcases,
            )
            metrics = result["metrics"]
            display = {
                "valid": metrics["false_negative"] == metrics["false_positive"] == 0,
                "suite_path": str(args.output.resolve() / "suite.json"),
                "case_count": len(result["cases"]),
                "metrics": metrics,
            }
        elif args.command == "start":
            result = start_agent_run(
                args.catalog,
                args.dataset,
                args.results_dir,
                fault_class=args.fault_class,
                testcase_id=args.testcase,
                model_id=args.model,
                mode=args.mode,
                run_id=args.run_id,
                rules_path=args.rules,
                prompt_path=args.prompt,
            )
        elif args.command == "finish":
            result = finish_agent_run(
                args.catalog,
                args.dataset,
                args.results_dir,
                run_id=args.run_id,
                checker_attempts=args.checker_attempts,
                notes=args.notes,
                rules_path=args.rules,
            )
        elif args.command == "restore":
            result = restore_agent_run(args.catalog, args.results_dir, run_id=args.run_id)
        else:
            result = summarize_agent_runs(args.results_dir)
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_bytes(pretty_json_bytes(result))
        _print(display or result)
        return 0
    except (AgentRunError, EvaluationSuiteError, FaultInjectionError, OSError, ValueError) as error:
        print(json.dumps({"valid": False, "error": str(error)}, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

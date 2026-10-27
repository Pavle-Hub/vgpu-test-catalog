"""Generate the deterministic paired Cursor experiment schedule."""

from __future__ import annotations

import argparse
import csv
import io
import random
from pathlib import Path

FAULT_CASES = [
    ("wrong-value", "TC-001"),
    ("stale-value", "TC-002"),
    ("hallucinated-field", "TC-003"),
    ("broken-format", "TC-004"),
    ("false-provenance", "TC-005"),
]
FIELDS = [
    "order",
    "pair_id",
    "run_id",
    "condition",
    "fault_class",
    "testcase_id",
    "repetition",
    "mode",
    "prompt_path",
]


def render_plan(version: str, *, seed: int = 2026, repetitions: int = 5) -> str:
    """Return a stable CSV schedule with paired and alternating agent modes."""

    pairs: list[tuple[str, str, str, str, int]] = []
    for fault_class, testcase_id in FAULT_CASES:
        for repetition in range(1, repetitions + 1):
            pairs.append(
                (
                    f"{fault_class}-r{repetition:02d}",
                    "fault",
                    fault_class,
                    testcase_id,
                    repetition,
                )
            )
    for repetition in range(1, repetitions + 1):
        pairs.append((f"clean-r{repetition:02d}", "clean", "", "", repetition))

    random.Random(seed).shuffle(pairs)
    rows: list[list[str | int]] = []
    order = 1
    for pair_index, (pair_id, condition, fault, testcase, repetition) in enumerate(
        pairs, start=1
    ):
        modes = ["with-checker", "without-checker"]
        if pair_index % 2 == 0:
            modes.reverse()
        for mode in modes:
            subject = "clean" if condition == "clean" else fault
            run_id = f"{version}-{subject}-r{repetition:02d}-{mode}"
            rows.append(
                [
                    order,
                    pair_id,
                    run_id,
                    condition,
                    fault,
                    testcase,
                    repetition,
                    mode,
                    f"eval/prompts/{mode}.md",
                ]
            )
            order += 1

    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(FIELDS)
    writer.writerows(rows)
    return output.getvalue()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not args.version.isalnum():
        parser.error("--version must be alphanumeric, for example v2")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(render_plan(args.version).encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

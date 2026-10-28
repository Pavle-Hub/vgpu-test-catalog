"""Reproducible thesis tables and static figures from corrected saved scores."""

from __future__ import annotations

import argparse
import json
from html import escape
from pathlib import Path
from typing import Any

from vgpu_catalog.hashing import sha256_bytes
from vgpu_eval.codex_batch import ROOT, BatchError, analyze, write_json

CLASSES = (
    ("wrong-value", "Pogrešna vrednost"),
    ("stale-value", "Zastarela vrednost"),
    ("hallucinated-field", "Izmišljeno polje"),
    ("broken-format", "Narušen format"),
    ("false-provenance", "Netačno poreklo"),
)
MODES = (("with-checker", "#2366A8"), ("without-checker", "#BD641C"))


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def collect_data(source: Path) -> dict[str, Any]:
    """Recompute aggregates from corrected attempts; never query a live agent."""
    source = source.resolve()
    collection = source.parent.parent
    plan = load(collection / "plan.json")
    frozen = load(collection / "frozen-protocol.json")
    correction = load(source / "correction.json")
    if correction["collection_head"] != frozen["identity"]["head"]:
        raise BatchError("Correction refers to a different frozen collection.")
    if plan != frozen["identity"]["plan"]:
        raise BatchError("Plan differs from frozen collection.")
    planned = {row["run_id"]: row for row in plan}
    fields = tuple(plan[0]) + (
        "status", "success", "checker_valid", "protected_fields_preserved",
        "scope_preserved", "checker_attempts", "human_review_reported",
    )
    attempts, hashes, completed = [], {}, set()
    for path in sorted((source / "runs").glob("*/*/result.json")):
        result = load(path)
        run_id = result["run_id"]
        if run_id not in planned or any(result.get(k) != v for k, v in planned[run_id].items()):
            raise BatchError("Result differs from planned matrix.")
        if result["status"] == "completed":
            if run_id in completed:
                raise BatchError(f"Duplicate completed run: {run_id}")
            completed.add(run_id)
        attempts.append({key: result[key] for key in fields})
        hashes[path.relative_to(collection).as_posix()] = sha256_bytes(path.read_bytes())
    summary = analyze(attempts, len(plan))
    if not summary["complete"] or summary != load(source / "summary.json"):
        raise BatchError("Corrected summary is incomplete or not reproducible.")
    for path in (collection / "plan.json", collection / "frozen-protocol.json",
                 source / "summary.json", source / "correction.json"):
        hashes[path.relative_to(collection).as_posix()] = sha256_bytes(path.read_bytes())
    return {
        "protocol_id": frozen["identity"]["config"]["protocol_id"],
        "collection_head": frozen["identity"]["head"],
        "agent": frozen["identity"]["config"]["agent"],
        "score_revision": "audit-v2", "source_collection": "eval/results/codex-eval-1",
        "source_sha256": hashes, "summary": summary, "attempts": attempts,
        "corrected_attempts": len(correction["changed_attempts"]),
        "human_review_stops": correction["human_review_stops"],
    }


def pct(value: float) -> str:
    return f"{100 * value:.1f}".replace(".", ",") + "%"


def cell(group: dict[str, Any]) -> str:
    return f"{group['successes']}/{group['n']} ({pct(group['rate'])})"


def interval(group: dict[str, Any]) -> str:
    low, high = group["wilson_95"]
    return f"{pct(low)}–{pct(high)}"


def tables(summary: dict[str, Any]) -> str:
    lines = [
        "# Tabele za diplomski rad — korigovano ocenjivanje audit-v2", "",
        "## Tabela 1. Autonomne popravke po klasi greške", "",
        "| Klasa | with-checker | 95% Wilson interval | without-checker | 95% Wilson interval |",
        "| --- | ---: | --- | ---: | --- |",
    ]
    for key, label in CLASSES:
        a, b = (summary["by_fault_class"][f"{key}/{mode}"] for mode, _ in MODES)
        lines.append(
            f"| {label} (`{key}`) | {cell(a)} | {interval(a)} | {cell(b)} | {interval(b)} |"
        )
    lines += [
        "", "Pet ponavljanja istog ciljnog kvara po klasi i režimu; ne pet različitih kvarova.",
        "", "## Tabela 2. Zbirno za slučajeve sa greškom", "",
        "| Režim | Uspešne popravke | 95% Wilson interval |",
        "| --- | ---: | --- |",
    ]
    for mode, _ in MODES:
        group = summary["groups"][f"fault/{mode}"]
        lines.append(f"| {mode} | {cell(group)} | {interval(group)} |")
    lines += [
        "", "## Tabela 3. Kontrole bez ubačene greške (odvojeno od popravki)", "",
        "| Režim | Uspešne kontrolne sesije | 95% Wilson interval |",
        "| --- | ---: | --- |",
    ]
    for mode, _ in MODES:
        group = summary["groups"][f"clean/{mode}"]
        lines.append(f"| {mode} | {cell(group)} | {interval(group)} |")
    lines += [
        "", "## Tabela 4. Upareni ishodi i eksplorativni egzaktni test", "",
        "| Grupa | Oba uspešna | Samo with | Samo without | Oba neuspešna | Razlika (pp) | p |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for key, label in (("fault", "Sa greškom"), ("clean", "Kontrole")):
        p = summary["paired"][key]
        delta = f"{100 * p['paired_rate_difference']:.1f}".replace(".", ",")
        pvalue = f"{p['exact_p_two_sided']:.3f}".replace(".", ",")
        lines.append(
            f"| {label} | {p['both_success']} | {p['with_only']} | {p['without_only']} "
            f"| {p['both_failure']} | {delta} | {pvalue} |"
        )
    lines += [
        "", "Razlika je with-checker minus without-checker, u procentnim poenima.",
        "Za kontrole nema nesaglasnih parova; p = 1 je konvencija, ne dokaz jednakosti.",
        "Intervali su marginalni opisni intervali pojedinačnih stopa, ne interval razlike.",
        "Jedan infrastrukturni prekid je neocenjen; pilot-sesije nisu uključene.",
        "Četiri strukturna kvara sa zahtevom za ljudski pregled ostaju neuspešne popravke.",
    ]
    return "\n".join(lines) + "\n"


def chart(summary: dict[str, Any], *, by_class: bool) -> dict[str, Any]:
    shapes: list[dict[str, Any]] = []

    def text(x: float, y: float, value: str, size: int = 19, color: str = "#263342") -> None:
        shapes.append({"type": "text", "x": x, "y": y, "text": value,
                       "size": size, "color": color})

    def line(x: float, y: float, x2: float, y2: float,
             color: str = "#DDE3E9", width: int = 1) -> None:
        shapes.append({"type": "line", "x": x, "y": y, "x2": x2, "y2": y2,
                       "color": color, "width": width})

    title = ("Autonomna popravka po klasi greške" if by_class
             else "Popravke i kontrole — odvojeni ishodi")
    text(46, 30, title, 30)
    text(46, 78, "Tačke: opažena uspešnost  |  Linije: 95% Wilson intervali", 20)
    for index, (mode, color) in enumerate(MODES):
        x = 48 + index * 270
        shapes.append({"type": "point", "x": x + 7, "y": 126, "color": color,
                       "square": bool(index)})
        text(x + 27, 113, mode, 20, color)
    left, right = 365, 955

    def axis(top: int, bottom: int) -> None:
        for tick in range(0, 101, 20):
            x = left + (right - left) * tick / 100
            line(x, top, x, bottom)
            text(x - 15, bottom + 13, f"{tick}", 17)
        text(545, bottom + 45, "Uspešnost (%)", 19)

    def point(group: dict[str, Any], y: float, index: int) -> None:
        _, color = MODES[index]
        low, high = group["wilson_95"]
        start, end = left + (right - left) * low, left + (right - left) * high
        line(start, y, end, y, color, 3)
        line(start, y - 6, start, y + 6, color, 2)
        line(end, y - 6, end, y + 6, color, 2)
        shapes.append({"type": "point", "x": left + (right - left) * group["rate"],
                       "y": y, "color": color, "square": bool(index)})
        text(989, y - 13, cell(group), 19, color)

    if by_class:
        axis(180, 645)
        for i, (key, label) in enumerate(CLASSES):
            y = 217 + i * 88
            text(46, y - 20, label, 21)
            text(46, y + 8, key, 16, "#607080")
            for j, (mode, _) in enumerate(MODES):
                point(summary["by_fault_class"][f"{key}/{mode}"], y - 10 + j * 28, j)
        failures = summary["by_fault_class"]["broken-format/with-checker"]
        count = failures["n"] - failures["successes"]
        text(46, 733, f"n = 5 po klasi i režimu. Neotklonjeni kvarovi: {count} "
             "(broken-format / with-checker).", 19)
        text(46, 767, "audit-v2 · isti ciljni kvar po klasi · studija nije opšti rang modela", 17)
        height = 815
    else:
        for i, (key, label) in enumerate((("fault", "Sa greškom (n = 25)"),
                                         ("clean", "Kontrole (n = 5)"))):
            top = 180 + i * 210
            axis(top, top + 100)
            text(46, top + 16, label, 22)
            text(46, top + 48, "Autonomna popravka" if key == "fault"
                 else "Uspešna kontrolna sesija", 17)
            for j, (mode, _) in enumerate(MODES):
                point(summary["groups"][f"{key}/{mode}"], top + 25 + j * 38, j)
        paired = summary["paired"]["fault"]
        delta = f"{100 * paired['paired_rate_difference']:.0f}".replace("-", "−")
        pvalue = f"{paired['exact_p_two_sided']:.3f}".replace(".", ",")
        text(46, 608, f"Popravke: with − without = {delta} pp; "
             f"egzaktni upareni test: p = {pvalue}.", 19)
        text(46, 644, "Kontrole su odvojene. Piloti i infrastrukturni prekid nisu ocenjeni.", 18)
        text(46, 680, "audit-v2 · opisni intervali · bez dokaza opšte prednosti jednog režima", 17)
        height = 725
    return {"width": 1250, "height": height, "shapes": shapes}


def svg(drawing: dict[str, Any]) -> bytes:
    width, height = drawing["width"], drawing["height"]
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
             f'viewBox="0 0 {width} {height}" role="img">',
             '<title>Rezultati korigovane analize audit-v2</title>',
             '<desc>Opažene stope uspeha i 95% Wilson intervali; kontrole su odvojene.</desc>',
             '<rect width="100%" height="100%" fill="white"/>']
    for item in drawing["shapes"]:
        x, y, color = item["x"], item["y"], item["color"]
        if item["type"] == "text":
            parts.append(f'<text x="{x}" y="{y + item["size"]}" font-size="{item["size"]}" '
                         f'font-family="Segoe UI,Arial,sans-serif" fill="{color}">'
                         f'{escape(item["text"])}</text>')
        elif item["type"] == "line":
            parts.append(f'<line x1="{x}" y1="{y}" x2="{item["x2"]}" y2="{item["y2"]}" '
                         f'stroke="{color}" stroke-width="{item["width"]}"/>')
        elif item["square"]:
            parts.append(f'<rect x="{x - 6}" y="{y - 6}" width="12" height="12" fill="{color}"/>')
        else:
            parts.append(f'<circle cx="{x}" cy="{y}" r="6" fill="{color}"/>')
    return ("\n".join(parts) + "\n</svg>\n").encode("utf-8")


def build(data: dict[str, Any], destination: Path, *, png: bool = False) -> None:
    if destination.exists():
        raise BatchError("Destination exists; refusing to overwrite thesis artifacts.")
    summary = analyze(data["attempts"], data["summary"]["expected_runs"])
    if summary != data["summary"] or not summary["complete"]:
        raise BatchError("Portable scored attempts do not reproduce the complete summary.")
    destination.mkdir(parents=True, exist_ok=False)
    write_json(destination / "data.json", data)
    (destination / "tables.md").write_bytes(tables(summary).encode("utf-8"))
    for name, by_class in (("by-class", True), ("overall-and-controls", False)):
        drawing = chart(summary, by_class=by_class)
        write_json(destination / f"{name}.drawing.json", drawing)
        (destination / f"{name}.svg").write_bytes(svg(drawing))
        if png:
            from vgpu_eval.png_render import render

            render(drawing, destination / f"{name}.png")
    write_json(destination / "manifest.json", {
        "source": "Corrected audit-v2 scores; no agent sessions invoked.",
        "source_sha256": data["source_sha256"],
        "generator_sha256": {
            name: sha256_bytes((ROOT / "src/vgpu_eval" / name).read_bytes())
            for name in ("results_figures.py", "png_render.py")
        },
        "files_sha256": {p.name: sha256_bytes(p.read_bytes())
                         for p in sorted(destination.iterdir()) if p.is_file()},
    })


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    inputs = parser.add_mutually_exclusive_group()
    inputs.add_argument("--source", type=Path)
    inputs.add_argument("--data", type=Path, help="Portable data.json for offline regeneration.")
    parser.add_argument("--destination", type=Path, default=ROOT / "docs/evidence/results-v1")
    parser.add_argument("--png", action="store_true", help="Also render 2x PNGs on Windows.")
    args = parser.parse_args()
    try:
        data = load(args.data) if args.data else collect_data(
            args.source or ROOT / "eval/results/codex-eval-1/reanalysis/audit-v2"
        )
        build(data, args.destination, png=args.png)
        print(f"Thesis tables and figures saved: {args.destination}")
        return 0
    except (OSError, ValueError, KeyError) as error:
        print(f"Figure generation stopped: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

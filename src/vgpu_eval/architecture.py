"""Static, code-referenced architecture and experiment diagrams for the thesis."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from vgpu_catalog.hashing import sha256_bytes
from vgpu_eval.codex_batch import ROOT, BatchError, git, write_json
from vgpu_eval.results_figures import svg

# Each mapping is an implementation reference, not a generated dependency graph.
REFERENCES = {
    "snapshot": ["src/vgpu_catalog/snapshot.py", "src/vgpu_catalog/validation.py"],
    "mcp": ["src/env_mcp/server.py", "src/env_mcp/service.py",
            "src/metrics_mcp/server.py", "src/metrics_mcp/service.py", ".codex/config.toml"],
    "contract": ["rules.yaml", "schemas/catalog-derived.schema.json",
                 ".agents/skills/sync-catalog/SKILL.md", ".cursor/skills/sync-catalog/SKILL.md"],
    "expected": ["src/vgpu_catalog/derivation.py"],
    "checker": ["src/catalog_check/checker.py", "src/catalog_check/cli.py"],
    "catalog": ["catalog/test_catalog.md"],
    "runner": ["src/vgpu_eval/codex_batch.py", "src/vgpu_eval/faults.py", "src/vgpu_eval/runs.py",
               "eval/codex-protocol.yaml"],
    "analysis": ["src/vgpu_eval/codex_reanalysis.py", "src/vgpu_eval/results_figures.py"],
    "ci": [".github/workflows/catalog-ci.yml"],
}


class Diagram:
    def __init__(self, title: str, description: str, height: int) -> None:
        self.drawing: dict[str, Any] = {
            "width": 1500, "height": height, "title": title,
            "description": description, "shapes": [],
        }
        self.nodes: dict[str, dict[str, Any]] = {}
        self.edges: list[dict[str, Any]] = []
        self.text(50, 28, title, 32)
        self.text(50, 82, description, 20)

    def text(self, x: int, y: int, text: str, size: int = 20,
             color: str = "#263342") -> None:
        self.drawing["shapes"].append({
            "type": "text", "x": x, "y": y, "text": text, "size": size, "color": color,
        })

    def line(self, start: tuple[int, int], end: tuple[int, int],
             color: str = "#52687B", width: int = 2) -> None:
        self.drawing["shapes"].append({
            "type": "line", "x": start[0], "y": start[1],
            "x2": end[0], "y2": end[1], "width": width, "color": color,
        })

    def node(self, key: str, x: int, y: int, width: int, height: int,
             lines: list[str]) -> None:
        self.nodes[key] = {"lines": lines, "bounds": [x, y, width, height]}
        corners = [(x, y), (x + width, y), (x + width, y + height), (x, y + height)]
        for i in range(4):
            self.line(corners[i], corners[(i + 1) % 4], "#AEBCC8", 1)
        for i, value in enumerate(lines):
            self.text(x + 18, y + 18 + 32 * i, value, 23 if i == 0 else 19)

    def arrow(self, source: str, target: str, label: str, points: list[tuple[int, int]],
              label_at: tuple[int, int] | None = None, *, feedback: bool = False) -> None:
        self.edges.append({"source": source, "target": target, "label": label,
                           "conditional": feedback})
        color = "#2366A8" if feedback else "#52687B"
        for a, b in zip(points, points[1:], strict=False):
            self.line(a, b, color)
        (x0, y0), (x, y) = points[-2:]
        dx = 0 if x == x0 else (1 if x > x0 else -1)
        dy = 0 if y == y0 else (1 if y > y0 else -1)
        for sign in (-1, 1):
            self.line((x, y), (x - 10 * dx + sign * 6 * dy,
                               y - 10 * dy - sign * 6 * dx), color)
        if label_at:
            self.text(*label_at, label, 17, color)

    def mermaid(self) -> str:
        lines = ["flowchart LR"]
        for key, node in self.nodes.items():
            lines.append(f"  {key}[{json.dumps('<br/>'.join(node['lines']), ensure_ascii=False)}]")
        for edge in self.edges:
            label = json.dumps(edge["label"], ensure_ascii=False)
            lines.append(f"  {edge['source']} -->|{label}| {edge['target']}")
        return "\n".join(lines) + "\n"


def maintenance() -> Diagram:
    d = Diagram("Arhitektura održavanja kataloga",
                "Logički tok podataka; plava povratna veza samo u režimu with-checker.", 1070)
    d.node("contract", 50, 175, 335, 155, [
        "Ugovor i skill", "rules.yaml · schemas", ".agents → .cursor/skills",
        "granice, režim i stop-uslovi",
    ])
    d.node("snapshot", 50, 430, 335, 175, [
        "Validirani snapshot", "dataset/runs.json", "capabilities.json · manifest.json",
        "hash i vreme izvora",
    ])
    d.node("mcp", 490, 405, 360, 260, [
        "Dva read-only MCP servera", "env-mcp: resources", "matrica i podržani GPU modeli",
        "metrics-mcp: tools", "list_testcases", "get_duration_stats · get_pass_rate",
    ])
    d.node("agent", 945, 175, 430, 210, [
        "AI agent / Codex CLI", "sync-catalog skill", "MCP dokazi + pravila",
        "predlog izmene kataloga", "granice određene uputstvima",
    ])
    d.node("catalog", 945, 490, 430, 190, [
        "catalog/test_catalog.md", "Purpose / Notes: očuvati",
        "Derived blocks: tačan ugovor", "Summary: semantički tekst",
        "jedini dozvoljeni izlaz agenta",
    ])
    d.node("expected", 50, 750, 335, 180, [
        "Očekivano stanje", "dataset + rules.yaml + schemas",
        "vgpu_catalog.derivation", "lokalno, bez LLM-a",
    ])
    d.node("checker", 490, 750, 360, 180, [
        "Deterministički checker", "predlog ↔ očekivano stanje",
        "JSON: valid + issues", "--check ne menja katalog",
    ])
    d.arrow("contract", "agent", "uputstva i pravila", [(385, 245), (945, 245)], (575, 214))
    d.arrow("snapshot", "mcp", "čitanje", [(385, 515), (490, 515)], (400, 482))
    d.arrow("mcp", "agent", "MCP stdio",
            [(850, 515), (900, 515), (900, 345), (945, 345)], (785, 357))
    d.arrow("agent", "catalog", "predlog / izmena", [(1160, 385), (1160, 490)], (1190, 423))
    d.arrow("snapshot", "expected", "lokalni proračun", [(220, 605), (220, 750)], (65, 670))
    d.arrow("expected", "checker", "referenca", [(385, 825), (490, 825)], (396, 792))
    d.arrow("catalog", "checker", "čita predlog",
            [(945, 580), (900, 580), (900, 825), (850, 825)], (922, 701))
    d.arrow("checker", "agent", "JSON povratna veza (samo with-checker)",
            [(850, 870), (1450, 870), (1450, 290), (1375, 290)], (965, 895), feedback=True)
    d.text(50, 975, "with-checker: najviše 3 agentska poziva provere. "
           "without-checker: 0 poziva i jedan predlog.", 21)
    d.text(50, 1015, "Završno ocenjivanje je odvojeno i postoji u oba režima (druga slika).", 20)
    return d


def evaluation() -> Diagram:
    d = Diagram("Eksperimenti i odvojena GitHub kontrola",
                "Ocenjivanje nije agentska povratna informacija; "
                "CI ne pokreće eksperimentalne sesije.",
                1085)
    d.text(50, 145, "A. Eksperimentalni tok — Codex batch runner", 24)
    definitions = [
        ("plan", 50, ["Zamrznut protokol", "model, promptovi i verzije",
                      "upareni raspored i seed", "snapshot i hash-evi"]),
        ("workspace", 415, ["Nova radna kopija", "ubrizgan kvar ili kontrola",
                           "početna provera evaluatora", "bez ispravne Git istorije"]),
        ("session", 780, ["Nova agentska sesija", "skill + lokalni MCP",
                         "with: do 3 checker poziva", "without: bez checker-a"]),
        ("score", 1145, ["Završni evaluator", "checker u oba režima",
                        "izvorni dataset i pravila", "zaštićena polja + scope"]),
    ]
    for key, x, lines in definitions:
        d.node(key, x, 200, 305, 170, lines)
    for a, b, x in (("plan", "workspace", 355), ("workspace", "session", 720),
                    ("session", "score", 1085)):
        d.arrow(a, b, "sledeći korak", [(x, 285), (x + 60, 285)])
    d.node("raw", 780, 480, 670, 155, [
        "Sačuvani dokazi i originalne ocene",
        "ulaz / izlaz, events.jsonl, checker izveštaji i audit",
        "eval/results/codex-eval-1/ — bez povratka agentu",
        "prekidi ostaju sačuvani, ali neocenjeni",
    ])
    d.node("analysis", 50, 480, 670, 155, [
        "Naknadna analiza i materijal za rad",
        "audit-v2: korekcija klasifikacije, bez novih sesija",
        "uparena statistika · odvojene kontrole · intervali",
        "tabele, grafikoni i reprezentativni primeri",
    ])
    d.arrow("score", "raw", "zapis rezultata", [(1300, 370), (1300, 480)], (1085, 409))
    d.arrow("raw", "analysis", "analiza", [(780, 558), (720, 558)])
    d.text(50, 690, "B. Razvojni tok — odvojeno od rada agenta i prikupljanja rezultata", 24)
    for key, x, lines in (
        ("pr", 50, ["Pull request", "promene koje šalje korisnik", "prema grani main"]),
        ("gate", 415, ["catalog-gate / Actions", "validacija i checker --check",
                       "testovi, stil i fault suite"]),
        ("ruleset", 780, ["GitHub ruleset", "obavezan status provere", "neuspeh blokira spajanje"]),
        ("merge", 1145, ["Odluka o merge-u", "nakon potrebnih provera", "potvrđuje korisnik"]),
    ):
        d.node(key, x, 765, 305, 140, lines)
    for a, b, x in (("pr", "gate", 355), ("gate", "ruleset", 720), ("ruleset", "merge", 1085)):
        d.arrow(a, b, "razvojni tok", [(x, 835), (x + 60, 835)])
    d.text(50, 958, "Ruleset je podešavanje na GitHub-u, nije Python komponenta ni deo MCP-a.", 21)
    d.text(50, 1000, "Prikazan je konfigurisan način rada, ne nova provera udaljenog servisa.", 20)
    return d


def build(destination: Path, *, png: bool = False) -> None:
    if destination.exists():
        raise BatchError("Destination exists; refusing to overwrite architecture artifacts.")
    sources = {path: sha256_bytes((ROOT / path).read_bytes())
               for paths in REFERENCES.values() for path in paths}
    destination.mkdir(parents=True, exist_ok=False)
    for name, diagram in (("maintenance", maintenance()), ("evaluation-and-ci", evaluation())):
        write_json(destination / f"{name}.drawing.json", diagram.drawing)
        write_json(destination / f"{name}.model.json", {
            "nodes": diagram.nodes, "edges": diagram.edges,
        })
        (destination / f"{name}.svg").write_bytes(svg(diagram.drawing))
        (destination / f"{name}.mmd").write_bytes(diagram.mermaid().encode("utf-8"))
        if png:
            from vgpu_eval.png_render import render

            render(diagram.drawing, destination / f"{name}.png")
    write_json(destination / "manifest.json", {
        "description": "Authored logical views checked against code; not a runtime trace.",
        "inspected_head": git("rev-parse", "HEAD"), "references": REFERENCES,
        "source_sha256": sources,
        "generator_sha256": {
            name: sha256_bytes((ROOT / "src/vgpu_eval" / name).read_bytes())
            for name in ("architecture.py", "results_figures.py", "png_render.py")
        },
        "files_sha256": {p.name: sha256_bytes(p.read_bytes())
                         for p in sorted(destination.iterdir()) if p.is_file()},
        "scope_limits": [
            "Skill and audit establish workflow constraints, not hardened isolation.",
            "without-checker excludes agent feedback, not independent final evaluation.",
            "Protected text comparison belongs to the workflow/evaluator, not checker alone.",
            "GitHub rulesets require separate hosted evidence; they are not inferred from CI YAML.",
        ],
    })


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, default=ROOT / "docs/evidence/architecture-v1")
    parser.add_argument("--png", action="store_true")
    args = parser.parse_args()
    try:
        build(args.destination, png=args.png)
        print(f"Architecture figures saved: {args.destination}")
        return 0
    except (OSError, ValueError) as error:
        print(f"Architecture generation stopped: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Render a report.md skeleton from static.json (+ optional benchmark.json).

The output is intentionally a SKELETON — verdict line and top-issues-to-fix
section are placeholders that the human evaluator must fill in. The script
exists to close the Step 1 → Step 6 friction noted in the iteration-4 UX
review: there was no path from machine output to human report.

Usage:
  python3 render_report.py --static static.json [--benchmark benchmark.json] [--out report.md]

If --benchmark is omitted, only the Static section is rendered and a note
is added that dynamic measurement was skipped.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional


def _load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def render_static(s: dict) -> list[str]:
    score = s.get("score", "n/a")
    hard_fail = s.get("hard_fail", "n/a")
    warnings = s.get("warnings", 0)
    out = [
        f"## Static (score: {score} / hard_fail: {hard_fail} / warnings: {warnings})",
        "",
        "| axis | result | severity | evidence |",
        "|---|---|---|---|",
    ]
    for c in s.get("checks", []):
        result = "pass" if c.get("passed") else "FAIL"
        ev = (c.get("evidence") or "").replace("|", "\\|")
        out.append(f"| {c.get('axis')} | {result} | {c.get('severity')} | {ev} |")
    out.append("")
    return out


def render_dynamic(b: dict) -> list[str]:
    s = b.get("run_summary", {})
    w = s.get("with_skill", {})
    n = s.get("without_skill", {})
    d = s.get("delta", {})

    def cell(group: dict, key: str) -> str:
        m = (group.get(key) or {}).get("mean")
        if m is None:
            missing = (group.get(key) or {}).get("missing", 0)
            return f"n/a ({missing} missing)" if missing else "n/a"
        return str(m)

    out = [
        "## Dynamic",
        "",
        "| metric | with_skill | without_skill | delta |",
        "|---|---|---|---|",
        f"| pass_rate | {cell(w, 'pass_rate')} | {cell(n, 'pass_rate')} | {d.get('pass_rate', 'n/a')} |",
        f"| time (s)  | {cell(w, 'time_seconds')} | {cell(n, 'time_seconds')} | {d.get('time_seconds', 'n/a')} |",
        f"| tokens    | {cell(w, 'tokens')} | {cell(n, 'tokens')} | {d.get('tokens', 'n/a')} |",
        "",
    ]
    diff = b.get("differentiating_assertions") or []
    if diff:
        out += ["## Differentiating assertions", ""]
        for d_ in diff:
            out.append(
                f"- `{d_['text']}` — with {d_['with_pass_rate']} / without {d_['without_pass_rate']}"
                + (f" (eval `{d_.get('eval_name', d_.get('eval_id'))}`)" if d_.get('eval_name') or d_.get('eval_id') is not None else "")
            )
        out.append("")
    return out


def render(static: dict, benchmark: Optional[dict], target: str) -> str:
    lines: list[str] = [
        f"# skill-eval report: {target}",
        "",
        "## Verdict",
        "<one-line judgment — choose exactly one of: Ship-ready / Needs work / Net negative. Optionally append `+ Inconclusive (high variance)` or `+ single-run, variance not measured` as an additive flag.>",
        "",
    ]
    lines += render_static(static)
    if benchmark:
        lines += render_dynamic(benchmark)
    else:
        lines += ["## Dynamic", "", "Skipped (no benchmark.json supplied). Static-only evaluation.", ""]
    lines += [
        "## Top issues to fix",
        "1. <fill in from static FAIL rows and differentiating assertions>",
        "2. ",
        "3. ",
        "",
        "## Files",
        "- static.json",
    ]
    if benchmark:
        lines += ["- benchmark.json", "- runs/eval-*/{with_skill,without_skill}/outputs/"]
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--static", required=True, help="Path to static.json")
    ap.add_argument("--benchmark", default=None, help="Path to benchmark.json (optional)")
    ap.add_argument("--out", default=None, help="Output report.md path (default: stdout)")
    args = ap.parse_args()

    static_p = Path(args.static)
    if not static_p.is_file():
        print(f"ERROR: {static_p} not found", file=sys.stderr)
        return 2
    static = _load(static_p)
    benchmark = _load(Path(args.benchmark)) if args.benchmark else None

    target = Path(static.get("target", "unknown")).name or "unknown"
    rendered = render(static, benchmark, target)

    if args.out:
        out_p = Path(args.out)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(rendered, encoding="utf-8")
        print(f"wrote {out_p}")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    sys.exit(main())

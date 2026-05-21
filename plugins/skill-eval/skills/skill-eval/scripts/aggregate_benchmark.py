#!/usr/bin/env python3
"""Aggregate per-run grading + timing into a single benchmark.json / benchmark.md.

Expects the workspace layout:

  <iteration-dir>/
    runs/
      eval-<id>/
        with_skill/   { outputs/, grading.json, timing.json }
        without_skill/ { outputs/, grading.json, timing.json }
    evals.json   (optional, supplies eval names)

Output schema matches skill-creator's benchmark.json (see references/schemas.md
in skill-creator) so the same viewer can render it.

Usage:
  python aggregate_benchmark.py <iteration-dir> --skill-name foo [--out benchmark.json]
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
from pathlib import Path
from typing import Optional


def safe_load(p: Path) -> Optional[dict]:
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def stats(xs: list[Optional[float]]) -> dict:
    """Aggregate stats while distinguishing missing data from 0.

    Inputs may contain `None` for runs that lack timing.json or other
    measurements. Missing values are excluded from mean/stddev so a
    half-instrumented benchmark does not silently report 0 as a real
    datapoint.
    """
    present = [x for x in xs if x is not None]
    missing = len(xs) - len(present)
    if not present:
        return {"mean": None, "stddev": None, "min": None, "max": None, "n": 0, "missing": missing}
    return {
        "mean": round(statistics.fmean(present), 3),
        "stddev": round(statistics.pstdev(present), 3) if len(present) > 1 else 0,
        "min": round(min(present), 3),
        "max": round(max(present), 3),
        "n": len(present),
        "missing": missing,
    }


def fmt_delta(a: Optional[float], b: Optional[float]) -> str:
    if a is None or b is None:
        return "n/a (missing data)"
    d = a - b
    sign = "+" if d >= 0 else ""
    return f"{sign}{round(d, 3)}"


def collect(iteration_dir: Path) -> tuple[list[dict], dict[int, str]]:
    runs: list[dict] = []
    eval_names: dict[int, str] = {}

    evals_meta = safe_load(iteration_dir / "evals.json") or {}
    for e in evals_meta.get("evals", []):
        if "id" in e:
            eval_names[int(e["id"])] = e.get("name") or e.get("prompt", "")[:60]

    runs_dir = iteration_dir / "runs"
    if not runs_dir.is_dir():
        return runs, eval_names

    for eval_dir in sorted(runs_dir.iterdir()):
        if not eval_dir.is_dir() or not eval_dir.name.startswith("eval-"):
            continue
        try:
            eval_id = int(eval_dir.name.split("-", 1)[1])
        except ValueError:
            continue
        for config in ("with_skill", "without_skill"):
            cfg_dir = eval_dir / config
            if not cfg_dir.is_dir():
                continue
            grading = safe_load(cfg_dir / "grading.json") or {}
            timing_raw = safe_load(cfg_dir / "timing.json")
            timing = timing_raw or {}
            expectations = grading.get("expectations", [])
            passed = sum(1 for x in expectations if x.get("passed"))
            total = len(expectations)
            pass_rate = (passed / total) if total else None

            # Distinguish "no timing.json" from "0 ms": both fields are
            # treated as missing when timing.json is absent OR when the
            # specific field is missing inside it.
            duration_s: Optional[float] = None
            if timing_raw is not None:
                if "total_duration_seconds" in timing:
                    duration_s = float(timing["total_duration_seconds"])
                elif "duration_ms" in timing:
                    duration_s = float(timing["duration_ms"]) / 1000.0
            tokens: Optional[int] = (
                int(timing["total_tokens"]) if (timing_raw is not None and "total_tokens" in timing) else None
            )

            runs.append({
                "eval_id": eval_id,
                "eval_name": eval_names.get(eval_id, f"eval-{eval_id}"),
                "configuration": config,
                "run_number": 1,
                "result": {
                    "pass_rate": round(pass_rate, 3) if pass_rate is not None else None,
                    "passed": passed,
                    "failed": total - passed,
                    "total": total,
                    "time_seconds": round(duration_s, 1) if duration_s is not None else None,
                    "tokens": tokens,
                    "tool_calls": 0,
                    "errors": 0,
                },
                "expectations": expectations,
                "_missing_fields": [
                    f for f in (
                        "grading.json" if not grading else None,
                        "timing.json" if timing_raw is None else None,
                    ) if f
                ],
            })
    return runs, eval_names


def summarize(runs: list[dict]) -> dict:
    summary: dict[str, dict] = {}
    for config in ("with_skill", "without_skill"):
        subset = [r for r in runs if r["configuration"] == config]
        summary[config] = {
            "pass_rate": stats([r["result"]["pass_rate"] for r in subset]),
            "time_seconds": stats([r["result"]["time_seconds"] for r in subset]),
            "tokens": stats([
                float(r["result"]["tokens"]) if r["result"]["tokens"] is not None else None
                for r in subset
            ]),
        }
    w = summary["with_skill"]
    b = summary["without_skill"]
    summary["delta"] = {
        "pass_rate": fmt_delta(w["pass_rate"]["mean"], b["pass_rate"]["mean"]),
        "time_seconds": fmt_delta(w["time_seconds"]["mean"], b["time_seconds"]["mean"]),
        "tokens": fmt_delta(w["tokens"]["mean"], b["tokens"]["mean"]),
    }
    return summary


def differentiating_assertions(runs: list[dict]) -> list[dict]:
    """Find assertions that pass much more often with_skill than without.

    Grouping is by (eval_id, text). Two different evals that share an
    assertion string are tracked separately so cross-eval pollution does
    not blur the with/without rates.
    """
    by_key: dict[tuple[int, str], dict[str, list[bool]]] = {}
    eval_names: dict[int, str] = {}
    for r in runs:
        eid = int(r["eval_id"])
        eval_names[eid] = r["eval_name"]
        for e in r.get("expectations", []):
            txt = e.get("text", "")
            if not txt:
                continue
            key = (eid, txt)
            by_key.setdefault(key, {"with_skill": [], "without_skill": []})
            by_key[key][r["configuration"]].append(bool(e.get("passed")))
    out = []
    for (eid, txt), m in by_key.items():
        if not m["with_skill"] or not m["without_skill"]:
            continue  # need at least one run in each config to compare
        w_rate = sum(m["with_skill"]) / len(m["with_skill"])
        b_rate = sum(m["without_skill"]) / len(m["without_skill"])
        if (w_rate - b_rate) >= 0.5:
            out.append({
                "eval_id": eid,
                "eval_name": eval_names.get(eid, f"eval-{eid}"),
                "text": txt,
                "with_pass_rate": round(w_rate, 2),
                "without_pass_rate": round(b_rate, 2),
            })
    return sorted(out, key=lambda x: -(x["with_pass_rate"] - x["without_pass_rate"]))


def _cell(s: dict) -> str:
    m = s.get("mean")
    if m is None:
        missing = s.get("missing", 0)
        return f"n/a ({missing} missing)" if missing else "n/a"
    return str(m)


def write_markdown(out_md: Path, payload: dict) -> None:
    s = payload["run_summary"]
    lines = [
        f"# benchmark: {payload['metadata']['skill_name']}",
        "",
        "## Summary",
        "",
        "| metric | with_skill | without_skill | delta |",
        "|---|---|---|---|",
        f"| pass_rate | {_cell(s['with_skill']['pass_rate'])} | {_cell(s['without_skill']['pass_rate'])} | {s['delta']['pass_rate']} |",
        f"| time (s)  | {_cell(s['with_skill']['time_seconds'])} | {_cell(s['without_skill']['time_seconds'])} | {s['delta']['time_seconds']} |",
        f"| tokens    | {_cell(s['with_skill']['tokens'])} | {_cell(s['without_skill']['tokens'])} | {s['delta']['tokens']} |",
        "",
        "## Per-eval",
        "",
        "| eval | config | pass | time | tokens |",
        "|---|---|---|---|---|",
    ]
    for r in payload["runs"]:
        lines.append(
            f"| {r['eval_name']} | {r['configuration']} | "
            f"{r['result']['passed']}/{r['result']['total']} | "
            f"{r['result']['time_seconds']}s | {r['result']['tokens']} |"
        )
    if payload.get("differentiating_assertions"):
        lines += ["", "## Differentiating assertions", ""]
        for a in payload["differentiating_assertions"]:
            lines.append(f"- `{a['text']}` — with {a['with_pass_rate']} / without {a['without_pass_rate']}")
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("iteration_dir")
    ap.add_argument("--skill-name", required=True)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    iteration_dir = Path(args.iteration_dir).resolve()
    runs, _ = collect(iteration_dir)
    summary = summarize(runs)
    diff = differentiating_assertions(runs)

    payload = {
        "metadata": {
            "skill_name": args.skill_name,
            "iteration_dir": str(iteration_dir),
            "evals_run": sorted({r["eval_id"] for r in runs}),
            "runs_per_configuration": 1,
        },
        "runs": runs,
        "run_summary": summary,
        "differentiating_assertions": diff,
        "notes": [],
    }

    out_path = Path(args.out) if args.out else iteration_dir / "benchmark.json"
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    write_markdown(out_path.with_suffix(".md"), payload)
    print(f"wrote {out_path}")
    print(f"wrote {out_path.with_suffix('.md')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Render a skill-eval workspace (iteration-N/) into a single self-contained HTML file.

Discovery rules (all optional — missing artefacts degrade gracefully):
  workspace/
    report.md           → Verdict (§04) + Top fixes (§07) parsed by H2 header
    static.json         → Static layer (§05)
    benchmark.json      → Dynamic layer (§06)
    evals.json          → Evals run (§03)
    NN-*.md             → Multi-angle sub-reports (appended after §08)

Design contract: references/frontend-design.md (Field Audit theme — Fraunces +
bone paper + vermillion accent, eight numbered sections, before/after fix cards).

Usage:
  python3 render_html.py <workspace-dir> [--out report.html] [--title "..."]
                                          [--open] [--serve [--port N]]

The chrome language (section titles, verdict labels, README pointer) is auto-detected
from `report.md` content: CJK >= 25% picks `ja`, otherwise `en`. The orchestrating
skill is expected to have already confirmed the language with the user (via
AskUserQuestion) before writing `report.md` in that language; the renderer simply
mirrors what `report.md` is written in.
"""

from __future__ import annotations

import argparse
import html
import http.server
import json
import re
import sys
import webbrowser
from functools import partial
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Localization — plugin overview + glossary copy hard-coded in two languages
# ---------------------------------------------------------------------------

LOCALES: dict[str, dict] = {
    "ja": {
        "report_kicker": "SKILL EVALUATION REPORT",
        "section_titles": {
            "evals": "このレポートで実行した eval",
            "verdict": "判定",
            "static": "静的層 (Static)",
            "dynamic": "動的層 (Dynamic — A/B benchmark)",
            "fixes": "修正候補 (Before / After)",
            "files": "ファイル一覧",
            "sub_reports": "補足: multi-angle sub-reports",
        },
        "readme_pointer": "プラグインの概要・用語集・トリガー条件は README を参照してください。このレポートはこの iteration の評価結果のみを扱います。",
        "verdict_label": "判定",
        "fix_problem": "問題",
        "fix_before": "修正前",
        "fix_after": "修正後",
        "fix_verify": "検証",
        "static_score": "Static スコア",
        "static_warnings": "warnings",
        "static_hard_fail": "hard_fail",
        "dynamic_pass_rate": "アサーション合格率 (pass_rate)",
        "dynamic_time": "実行時間 (秒)",
        "dynamic_tokens": "トークン消費量",
        "dynamic_with": "with_skill",
        "dynamic_without": "without_skill",
        "dynamic_delta": "Δ (差分)",
        "per_eval_heading": "eval ごとの内訳",
        "diff_heading": "差別化アサーション",
        "diff_empty": "with / without で 0.5 以上の差がついた assertion はありません。",
        "files_lead": "この workspace に存在するアーティファクト:",
        "no_report": "report.md が見つかりません。skill-eval Step 6 を実行してから再度 viewer を呼んでください。",
        "no_evals": "evals.json が見つかりません。skill-eval Step 2 で確認したプロンプトを workspace に書き出してください。",
    },
    "en": {
        "report_kicker": "SKILL EVALUATION REPORT",
        "section_titles": {
            "evals": "Evals run in this report",
            "verdict": "Verdict",
            "static": "Static layer",
            "dynamic": "Dynamic layer (A/B benchmark)",
            "fixes": "Top fixes (before / after)",
            "files": "Files in this workspace",
            "sub_reports": "Appendix: multi-angle sub-reports",
        },
        "readme_pointer": "Plugin overview, glossary, and trigger criteria live in the README. This report covers only the results of this iteration.",
        "verdict_label": "Verdict",
        "fix_problem": "Problem",
        "fix_before": "Before",
        "fix_after": "After",
        "fix_verify": "Verification",
        "static_score": "Static score",
        "static_warnings": "warnings",
        "static_hard_fail": "hard_fail",
        "dynamic_pass_rate": "Assertion pass rate",
        "dynamic_time": "Time (seconds)",
        "dynamic_tokens": "Tokens consumed",
        "dynamic_with": "with_skill",
        "dynamic_without": "without_skill",
        "dynamic_delta": "Δ (delta)",
        "per_eval_heading": "Per-eval breakdown",
        "diff_heading": "Differentiating assertions",
        "diff_empty": "No assertion showed a with/without gap of 0.5 or more.",
        "files_lead": "Artefacts present in this workspace:",
        "no_report": "No report.md found. Run skill-eval Step 6 first, then re-invoke the viewer.",
        "no_evals": "No evals.json found in the workspace. Copy the confirmed eval set from Step 2 into the workspace.",
    },
}


def detect_language(text: str) -> str:
    """Pick 'ja' if ≥ 25% of the first 400 non-space chars are CJK, else 'en'."""
    if not text:
        return "en"
    sample = re.sub(r"\s", "", text)[:400]
    if not sample:
        return "en"
    cjk = sum(1 for ch in sample if "぀" <= ch <= "ヿ" or "一" <= ch <= "鿿" or "ｦ" <= ch <= "ﾟ")
    return "ja" if cjk / len(sample) >= 0.25 else "en"


# ---------------------------------------------------------------------------
# Minimal markdown → HTML (stdlib regex, no external deps)
# ---------------------------------------------------------------------------

_INLINE_CODE = re.compile(r"`([^`\n]+)`")
_BOLD = re.compile(r"\*\*([^*\n]+)\*\*")
_LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
_LIST_ITEM = re.compile(r"^(\s*)[-*]\s+(.*)$")
_NUM_LIST_ITEM = re.compile(r"^(\s*)\d+\.\s+(.*)$")
_TABLE_SEP = re.compile(r"^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?\s*$")


def _inline(text: str) -> str:
    parts: list[tuple[str, str]] = []

    def stash(m: re.Match) -> str:
        parts.append(("code", m.group(1)))
        return f"\x00{len(parts)-1}\x00"

    text = _INLINE_CODE.sub(stash, text)
    text = _BOLD.sub(r"<strong>\1</strong>", text)
    text = _LINK.sub(lambda m: f'<a href="{html.escape(m.group(2), quote=True)}">{m.group(1)}</a>', text)

    def unstash(m: re.Match) -> str:
        idx = int(m.group(0).strip("\x00"))
        _, content = parts[idx]
        return f"<code>{html.escape(content)}</code>"

    text = re.sub(r"\x00(\d+)\x00", unstash, text)
    return text


def md_to_html(md: str) -> str:
    lines = md.splitlines()
    out: list[str] = []
    i = 0
    in_code = False
    code_buf: list[str] = []
    code_lang = ""

    def flush_para(buf: list[str]) -> None:
        if not buf:
            return
        para_text = " ".join(buf).strip()
        if para_text:
            out.append(f"<p>{_inline(html.escape(para_text))}</p>")
        buf.clear()

    para_buf: list[str] = []

    while i < len(lines):
        line = lines[i]

        fence_match = re.match(r"^(```|~~~)(.*)$", line)
        if fence_match:
            if in_code:
                lang = code_lang
                code_html = html.escape("\n".join(code_buf))
                lang_attr = f' data-lang="{html.escape(lang, quote=True)}"' if lang else ""
                out.append(f"<pre><code{lang_attr}>{code_html}</code></pre>")
                in_code = False
                code_buf.clear()
                code_lang = ""
            else:
                flush_para(para_buf)
                in_code = True
                code_lang = fence_match.group(2).strip()
            i += 1
            continue
        if in_code:
            code_buf.append(line)
            i += 1
            continue

        if not line.strip():
            flush_para(para_buf)
            i += 1
            continue

        h = _HEADING.match(line)
        if h:
            flush_para(para_buf)
            level = len(h.group(1))
            text = _inline(html.escape(h.group(2).strip()))
            out.append(f"<h{level}>{text}</h{level}>")
            i += 1
            continue

        if "|" in line and i + 1 < len(lines) and _TABLE_SEP.match(lines[i + 1]):
            flush_para(para_buf)
            header_cells = [c.strip() for c in line.strip().strip("|").split("|")]
            i += 2
            rows: list[list[str]] = []
            while i < len(lines) and "|" in lines[i] and lines[i].strip():
                if _TABLE_SEP.match(lines[i]):
                    i += 1
                    continue
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                rows.append(cells)
                i += 1
            table_html = ["<table>", "<thead><tr>"]
            for c in header_cells:
                table_html.append(f"<th>{_inline(html.escape(c))}</th>")
            table_html.append("</tr></thead><tbody>")
            for row in rows:
                table_html.append("<tr>")
                for c in row:
                    table_html.append(f"<td>{_inline(html.escape(c))}</td>")
                table_html.append("</tr>")
            table_html.append("</tbody></table>")
            out.append("".join(table_html))
            continue

        ul_m = _LIST_ITEM.match(line)
        ol_m = _NUM_LIST_ITEM.match(line)
        if ul_m or ol_m:
            flush_para(para_buf)
            tag = "ol" if ol_m else "ul"
            out.append(f"<{tag}>")
            while i < len(lines):
                m2 = _LIST_ITEM.match(lines[i]) if tag == "ul" else _NUM_LIST_ITEM.match(lines[i])
                if not m2:
                    break
                out.append(f"<li>{_inline(html.escape(m2.group(2).strip()))}</li>")
                i += 1
            out.append(f"</{tag}>")
            continue

        if re.match(r"^---+\s*$", line):
            flush_para(para_buf)
            out.append("<hr/>")
            i += 1
            continue

        para_buf.append(line.strip())
        i += 1

    flush_para(para_buf)
    if in_code and code_buf:
        out.append(f"<pre><code>{html.escape(chr(10).join(code_buf))}</code></pre>")

    return "\n".join(out)


# ---------------------------------------------------------------------------
# report.md parsers
# ---------------------------------------------------------------------------

# Header → semantic key. Case-insensitive substring match.
_SECTION_PATTERNS: list[tuple[str, list[str]]] = [
    ("verdict", ["verdict", "判定"]),
    ("static", ["static", "静的"]),
    ("dynamic", ["dynamic", "動的"]),
    ("differentiating", ["differentiating", "差別化"]),
    ("fixes", ["top issue", "top issues", "top fix", "top fixes", "修正候補", "fix"]),
    ("files", ["files", "ファイル"]),
]


def classify_section(header_text: str) -> Optional[str]:
    h = header_text.strip().lower()
    for key, patterns in _SECTION_PATTERNS:
        for pat in patterns:
            if pat.lower() in h:
                return key
    return None


def split_report_sections(md: str) -> dict[str, str]:
    """Slice report.md by H2 headers into {semantic_key: body_markdown}."""
    if not md:
        return {}
    sections: dict[str, list[str]] = {}
    current: Optional[str] = None
    header_buf: Optional[str] = None
    body: list[str] = []
    for line in md.splitlines():
        m = re.match(r"^##\s+(.+?)\s*$", line)
        if m:
            # flush previous
            if current is not None:
                sections.setdefault(current, []).extend(body)
                if header_buf:
                    sections[current].insert(0, header_buf)
            body = []
            header_buf = line  # remember the raw header line for verdict prelude
            key = classify_section(m.group(1))
            current = key or "_other_" + re.sub(r"\W+", "_", m.group(1))[:32]
            continue
        if current is None:
            continue
        body.append(line)
    if current is not None:
        sections.setdefault(current, []).extend(body)
    return {k: "\n".join(v).strip() for k, v in sections.items()}


def extract_verdict(verdict_md: str) -> tuple[str, str]:
    """From the Verdict section body, return (one_line_label, reasoning_paragraph)."""
    if not verdict_md:
        return ("", "")
    lines = verdict_md.splitlines()
    # Drop the H2 header line if present
    if lines and lines[0].lstrip().startswith("## "):
        lines = lines[1:]
    text = "\n".join(lines).strip()
    # First non-empty line is the label; rest is reasoning.
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not paragraphs:
        return ("", "")
    first = paragraphs[0]
    # If the first paragraph leads with **label** — use the bold span; else use the whole paragraph as label.
    label_m = re.match(r"\*\*([^*]+)\*\*", first)
    if label_m:
        label = label_m.group(1).strip()
        rest = first[label_m.end():].lstrip(" —–-:").strip()
        reasoning_parts = ([rest] if rest else []) + paragraphs[1:]
        return (label, "\n\n".join(reasoning_parts))
    return (first, "\n\n".join(paragraphs[1:]))


def parse_fix_blocks(fixes_md: str, lang: str) -> list[dict]:
    """Parse the Top-fixes section body into a list of fix dicts.

    Accepts two shapes:
    (a) New shape — each fix is an H3 (or numbered ###) with labeled blocks
        '問題 / 修正前 / 修正後 / 検証' (or English equivalents).
    (b) Legacy shape — each fix is a numbered list item with rank/category prose.
        We render this as a single 'problem' block with no before/after split.
    """
    if not fixes_md:
        return []

    # Remove the H2 header line if present
    body = re.sub(r"^##\s+.*$", "", fixes_md, count=1, flags=re.M).strip()

    # First try splitting by H3 headers as fix boundaries.
    fix_chunks = re.split(r"^###\s+", body, flags=re.M)
    if len(fix_chunks) > 1:
        chunks = fix_chunks[1:]
        return [_parse_fix_chunk(c, lang) for c in chunks]

    # Otherwise try numbered top-level items.
    items: list[str] = []
    current: list[str] = []
    for line in body.splitlines():
        if re.match(r"^\d+\.\s+", line):
            if current:
                items.append("\n".join(current).strip())
            current = [re.sub(r"^\d+\.\s+", "", line)]
        else:
            if current is not None:
                current.append(line)
    if current:
        items.append("\n".join(current).strip())
    items = [it for it in items if it]
    if not items:
        return []
    return [_parse_fix_chunk(it, lang) for it in items]


def _parse_fix_chunk(chunk: str, lang: str) -> dict:
    """Extract title, metadata, problem, before, after, verify from a single fix block."""
    lines = chunk.splitlines()
    title = lines[0].strip() if lines else ""
    body = "\n".join(lines[1:]).strip()

    # Metadata header line — look for `rank=` / `category=` etc.
    metadata = ""
    md_match = re.search(r"((?:rank|category|priority|source|effort|estimated_effort)\s*[=:][^\n]+)", body)
    if md_match:
        # Capture the whole metadata-ish line containing the match
        for line in body.splitlines():
            if md_match.group(1).split()[0].split("=")[0].split(":")[0] in line and ("=" in line or ":" in line):
                if any(tok in line.lower() for tok in ("rank", "category", "priority", "source")):
                    metadata = line.strip().strip("*").strip("_").strip()
                    break

    # Block label patterns — Japanese OR English.
    block_patterns = {
        "problem": [r"^(?:\*\*)?\s*(?:問題|Problem)\b", r"問題\s*\(Problem\)", r"Problem\s*\(問題\)"],
        "before": [r"^(?:\*\*)?\s*(?:修正前|Before)\b", r"修正前\s*\(Before\)", r"Before\s*\(修正前\)"],
        "after": [r"^(?:\*\*)?\s*(?:修正後|After)\b", r"修正後\s*\(After\)", r"After\s*\(修正後\)"],
        "verify": [
            r"^(?:\*\*)?\s*(?:検証|Verifiability|Verification|How to verify)\b",
            r"検証\s*\(Verifiability\)",
            r"Verifiability\s*\(検証\)",
        ],
    }

    # Walk lines, classifying each into a block bucket
    blocks: dict[str, list[str]] = {"problem": [], "before": [], "after": [], "verify": []}
    free: list[str] = []  # lines before any labelled block
    current: Optional[str] = None
    for line in body.splitlines():
        stripped = line.strip()
        matched = None
        for key, pats in block_patterns.items():
            if any(re.match(pat, stripped, flags=re.I) for pat in pats):
                matched = key
                break
        if matched is not None:
            current = matched
            # Strip the label tokens themselves from the first line so the body is clean
            cleaned = re.sub(r"^[*_\s]*(?:問題|修正前|修正後|検証|Problem|Before|After|Verifiability|Verification)\b\s*\(?[^)]*\)?\s*[—–\-:]*\s*", "", stripped, flags=re.I)
            cleaned = cleaned.strip("*").strip()
            if cleaned:
                blocks[current].append(cleaned)
            continue
        if current is None:
            free.append(line)
        else:
            blocks[current].append(line)

    # If nothing labelled, dump the whole body into `problem` for graceful degradation.
    has_labelled = any(blocks[k] for k in blocks)
    if not has_labelled:
        blocks["problem"] = body.splitlines()

    # Normalize: strip metadata line out of each block body
    def _clean(text_lines: list[str]) -> str:
        joined = "\n".join(text_lines).strip()
        if metadata:
            joined = joined.replace(metadata, "").strip()
        return joined

    return {
        "title": title.strip("*").strip(),
        "metadata": metadata,
        "free_prelude": "\n".join(free).strip(),
        "problem": _clean(blocks["problem"]),
        "before": _clean(blocks["before"]),
        "after": _clean(blocks["after"]),
        "verify": _clean(blocks["verify"]),
    }


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------


def render_evals(evals_data: Optional[dict], lang: str) -> str:
    L = LOCALES[lang]
    parts = ['<section id="evals"><h2>' + html.escape(L["section_titles"]["evals"]) + '</h2>']
    if not evals_data:
        parts.append(f'<p class="empty-note">{html.escape(L["no_evals"])}</p>')
        parts.append('</section>')
        return "\n".join(parts)
    for ev in evals_data.get("evals", []):
        eid = ev.get("id", "?")
        name = ev.get("name", f"eval-{eid}")
        desc = ev.get("description") or ev.get("prompt", "")
        prompt = ev.get("prompt", "")
        assertions = ev.get("assertions", [])
        parts.append('<article class="eval-card">')
        parts.append(f'<header class="eval-card-head"><span class="eval-id">eval-{html.escape(str(eid))}</span><h3>{html.escape(str(name))}</h3></header>')
        parts.append(f'<p class="eval-desc">{html.escape(str(desc))}</p>')
        if prompt and prompt != desc:
            parts.append(f'<div class="eval-prompt-label">prompt</div><pre class="eval-prompt"><code>{html.escape(str(prompt))}</code></pre>')
        if assertions:
            parts.append('<div class="eval-assertions-label">assertions</div><ul class="eval-assertions">')
            for a in assertions:
                kind = a.get("kind", "")
                text = a.get("text", "")
                kind_html = f'<span class="kind-tag">{html.escape(str(kind))}</span>' if kind else ""
                parts.append(f'<li>{kind_html}<span class="assertion-text">{html.escape(str(text))}</span></li>')
            parts.append('</ul>')
        parts.append('</article>')
    parts.append('</section>')
    return "\n".join(parts)


def _verdict_class(label: str) -> str:
    low = label.lower()
    if "ship-ready" in low or "shipready" in low:
        return "verdict-ship"
    if "needs work" in low or "needs-work" in low:
        return "verdict-needs"
    if "net negative" in low or "net-negative" in low:
        return "verdict-net-negative"
    if "inconclusive" in low:
        return "verdict-inconclusive"
    return "verdict-default"


def render_verdict(verdict_md: str, lang: str) -> str:
    L = LOCALES[lang]
    label, reasoning = extract_verdict(verdict_md)
    if not label and not reasoning:
        return (
            '<section id="verdict"><h2>' + html.escape(L["section_titles"]["verdict"]) + '</h2>'
            f'<p class="empty-note">{html.escape(L["no_report"])}</p></section>'
        )
    cls = _verdict_class(label)
    reasoning_html = md_to_html(reasoning) if reasoning else ""
    return (
        '<section id="verdict"><h2>' + html.escape(L["section_titles"]["verdict"]) + '</h2>'
        f'<article class="verdict-hero {cls}">'
        f'<span class="verdict-kicker">{html.escape(L["verdict_label"])}</span>'
        f'<p class="verdict-label">{_inline(html.escape(label))}</p>'
        f'<div class="verdict-reasoning">{reasoning_html}</div>'
        '</article>'
        '</section>'
    )


def render_static_section(static_data: Optional[dict], lang: str) -> str:
    L = LOCALES[lang]
    parts = ['<section id="static"><h2>' + html.escape(L["section_titles"]["static"]) + '</h2>']
    if not static_data:
        parts.append('<p class="empty-note">static.json not found.</p></section>')
        return "\n".join(parts)
    score = static_data.get("score")
    hard_fail = static_data.get("hard_fail")
    warnings = static_data.get("warnings", 0)
    checks = static_data.get("checks", [])
    target = static_data.get("target", "")

    if isinstance(score, (int, float)) and score >= 0.8 and not hard_fail:
        score_class = "score-ok"
    elif hard_fail:
        score_class = "score-fail"
    else:
        score_class = "score-warn"
    score_text = f"{score}" if score is not None else "n/a"

    parts.append(
        '<div class="static-headline">'
        f'<div class="static-score-wrap {score_class}">'
        f'<span class="static-score-label">{html.escape(L["static_score"])}</span>'
        f'<span class="static-score-value">{html.escape(score_text)}</span>'
        '</div>'
        '<div class="static-side-badges">'
        f'<span class="badge {("fail" if hard_fail else "ok")}">{html.escape(L["static_hard_fail"])}: {"true" if hard_fail else "false"}</span>'
        f'<span class="badge warn">{html.escape(L["static_warnings"])}: {warnings}</span>'
        '</div>'
        '</div>'
    )
    if target:
        parts.append(f'<p class="muted">target: <code>{html.escape(str(target))}</code></p>')

    parts.append('<div class="table-scroll"><table class="static-checks"><thead><tr><th>axis</th><th>result</th><th>severity</th><th>evidence</th></tr></thead><tbody>')
    for c in checks:
        passed = bool(c.get("passed"))
        severity = c.get("severity", "")
        row_class = "row-pass" if passed else (f"row-fail-{severity}" if severity else "row-fail")
        result_label = "pass" if passed else "FAIL"
        parts.append(
            f'<tr class="{row_class}">'
            f'<td><code>{html.escape(str(c.get("axis", "")))}</code></td>'
            f'<td class="result-cell">{result_label}</td>'
            f'<td><span class="sev-{html.escape(severity)}">{html.escape(severity)}</span></td>'
            f'<td>{html.escape(str(c.get("evidence", "")))}</td>'
            f'</tr>'
        )
    parts.append('</tbody></table></div>')
    parts.append('</section>')
    return "\n".join(parts)


def _stat_cell_text(d: Optional[dict], key: str) -> str:
    if not isinstance(d, dict):
        return "n/a"
    block = d.get(key) or {}
    m = block.get("mean")
    if m is None:
        missing = block.get("missing", 0)
        return f"n/a ({missing} missing)" if missing else "n/a"
    stddev = block.get("stddev")
    if stddev:
        return f"{m} ± {stddev}"
    return f"{m}"


def render_dynamic_section(bench_data: Optional[dict], lang: str) -> str:
    L = LOCALES[lang]
    parts = ['<section id="dynamic"><h2>' + html.escape(L["section_titles"]["dynamic"]) + '</h2>']
    if not bench_data:
        parts.append('<p class="empty-note">benchmark.json not found — dynamic layer skipped.</p></section>')
        return "\n".join(parts)
    meta = bench_data.get("metadata", {})
    run_summary = bench_data.get("run_summary", {})
    runs = bench_data.get("runs", [])
    diffs = bench_data.get("differentiating_assertions", [])

    parts.append(
        f'<p class="muted">skill: <code>{html.escape(str(meta.get("skill_name", "")))}</code> · '
        f'evals: {len(meta.get("evals_run", []))} · '
        f'runs/configuration: {meta.get("runs_per_configuration", "?")}</p>'
    )

    metric_rows: list[tuple[str, str, str, str]] = []
    delta = run_summary.get("delta", {})
    for metric_key, label in (
        ("pass_rate", L["dynamic_pass_rate"]),
        ("time_seconds", L["dynamic_time"]),
        ("tokens", L["dynamic_tokens"]),
    ):
        metric_rows.append(
            (
                label,
                _stat_cell_text(run_summary.get("with_skill"), metric_key),
                _stat_cell_text(run_summary.get("without_skill"), metric_key),
                str(delta.get(metric_key, "n/a")),
            )
        )

    parts.append('<div class="metric-grid">')
    parts.append(
        '<div class="metric-grid-head">'
        f'<span></span>'
        f'<span class="metric-col-label">{html.escape(L["dynamic_with"])}</span>'
        f'<span class="metric-col-label">{html.escape(L["dynamic_without"])}</span>'
        f'<span class="metric-col-label">{html.escape(L["dynamic_delta"])}</span>'
        '</div>'
    )
    for label, w, b, d in metric_rows:
        parts.append(
            '<div class="metric-row">'
            f'<span class="metric-name">{html.escape(label)}</span>'
            f'<span class="metric-val with">{html.escape(w)}</span>'
            f'<span class="metric-val without">{html.escape(b)}</span>'
            f'<span class="metric-val delta">{html.escape(d)}</span>'
            '</div>'
        )
    parts.append('</div>')

    if runs:
        parts.append(f'<h3>{html.escape(L["per_eval_heading"])}</h3>')
        parts.append('<div class="table-scroll"><table class="per-eval"><thead><tr><th>eval</th><th>configuration</th><th>run</th><th>pass</th><th>time</th><th>tokens</th></tr></thead><tbody>')
        for r in runs:
            res = r.get("result", {})
            parts.append(
                f"<tr>"
                f"<td>{html.escape(str(r.get('eval_name', r.get('eval_id', ''))))}</td>"
                f"<td><span class='config-{html.escape(str(r.get('configuration', '')))}'>{html.escape(str(r.get('configuration', '')))}</span></td>"
                f"<td>{html.escape(str(r.get('run_number', '?')))}</td>"
                f"<td>{html.escape(str(res.get('passed', 0)))}/{html.escape(str(res.get('total', 0)))}</td>"
                f"<td>{html.escape(str(res.get('time_seconds', 'n/a')))}</td>"
                f"<td>{html.escape(str(res.get('tokens', 'n/a')))}</td>"
                f"</tr>"
            )
        parts.append('</tbody></table></div>')

    parts.append(f'<h3>{html.escape(L["diff_heading"])}</h3>')
    if diffs:
        parts.append('<ul class="diff-list">')
        for d in diffs:
            with_rate = d.get("with_pass_rate", 0)
            without_rate = d.get("without_pass_rate", 0)
            ev_name = d.get("eval_name", d.get("eval_id", ""))
            parts.append(
                '<li class="diff-item">'
                f'<div class="diff-text">{html.escape(str(d.get("text", "")))}</div>'
                f'<div class="diff-meta">eval: <code>{html.escape(str(ev_name))}</code></div>'
                '<div class="diff-rates">'
                f'<span class="diff-rate diff-with">with {with_rate}</span>'
                f'<span class="diff-rate diff-without">without {without_rate}</span>'
                '</div>'
                '</li>'
            )
        parts.append('</ul>')
    else:
        parts.append(f'<p class="muted">{html.escape(L["diff_empty"])}</p>')

    parts.append('</section>')
    return "\n".join(parts)


def render_top_fixes(fixes_md: str, lang: str) -> str:
    L = LOCALES[lang]
    fixes = parse_fix_blocks(fixes_md, lang)
    parts = ['<section id="fixes"><h2>' + html.escape(L["section_titles"]["fixes"]) + '</h2>']
    if not fixes:
        parts.append('<p class="empty-note">No top fixes proposed.</p></section>')
        return "\n".join(parts)
    for idx, fx in enumerate(fixes, start=1):
        title = fx.get("title", f"fix-{idx}")
        metadata = fx.get("metadata", "")
        prelude = fx.get("free_prelude", "")
        parts.append(f'<article class="fix-card">')
        parts.append(f'<header class="fix-card-head"><span class="fix-rank">#{idx}</span><h3>{_inline(html.escape(title))}</h3></header>')
        if metadata:
            parts.append(f'<div class="fix-meta">{_inline(html.escape(metadata))}</div>')
        if prelude:
            parts.append(f'<div class="fix-prelude">{md_to_html(prelude)}</div>')
        for key, label_key, css_class in (
            ("problem", "fix_problem", "fix-block fix-problem"),
            ("before", "fix_before", "fix-block fix-before"),
            ("after", "fix_after", "fix-block fix-after"),
            ("verify", "fix_verify", "fix-block fix-verify"),
        ):
            content = fx.get(key, "")
            if not content:
                continue
            parts.append(
                f'<div class="{css_class}">'
                f'<div class="fix-block-kicker">{html.escape(L[label_key])}</div>'
                f'<div class="fix-block-body">{md_to_html(content)}</div>'
                '</div>'
            )
        parts.append('</article>')
    parts.append('</section>')
    return "\n".join(parts)


def render_files_section(workspace: Path, lang: str) -> str:
    L = LOCALES[lang]
    keys = ["report.md", "report.html", "static.json", "benchmark.json", "benchmark.md", "evals.json"]
    parts = ['<section id="files"><h2>' + html.escape(L["section_titles"]["files"]) + '</h2>']
    parts.append(f'<p>{html.escape(L["files_lead"])}</p>')
    parts.append('<ul class="file-list">')
    for name in keys:
        p = workspace / name
        if p.exists():
            parts.append(f'<li><code>{html.escape(str(p))}</code></li>')
    # Also surface runs/ structure (1-level)
    runs_dir = workspace / "runs"
    if runs_dir.is_dir():
        for child in sorted(runs_dir.iterdir()):
            if child.is_dir():
                parts.append(f'<li><code>{html.escape(str(child))}/</code></li>')
    parts.append('</ul></section>')
    return "\n".join(parts)


def render_sub_reports(sub_reports: list[tuple[str, Path, str]], lang: str) -> str:
    if not sub_reports:
        return ""
    L = LOCALES[lang]
    parts = ['<section id="sub-reports"><h2>' + html.escape(L["section_titles"]["sub_reports"]) + '</h2>']
    for stem, _p, content in sub_reports:
        sid = _slug(stem)
        parts.append(f'<details id="{sid}"><summary>{html.escape(stem)}</summary>')
        parts.append(md_to_html(content))
        parts.append('</details>')
    parts.append('</section>')
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Design — "Field Audit" theme
# ---------------------------------------------------------------------------

HEAD_EXTRAS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com"/>'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>'
    '<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600;9..144,700&display=swap" rel="stylesheet"/>'
)

CSS = r"""
:root {
  --bg: #f7f3ea; --paper: #fdf9f0; --ink: #1c1814; --ink-soft: #3a342c;
  --muted: #6b665a; --rule: #d8d0bd; --rule-strong: #4a4136;
  --accent: #c8421f; --accent-soft: #f3dcd2;
  --ok: #2b5a31; --ok-bg: #d5e5d2;
  --warn: #7a5c00; --warn-bg: #f3e6b3;
  --fail: #8a1f0e; --fail-bg: #f0cdc4;
  --info: #1a3a5c; --info-bg: #c8dde9;
  --font-display: "Fraunces", ui-serif, "Charter", Georgia, serif;
  --font-body: ui-serif, "Charter", "Iowan Old Style", Georgia, serif;
  --font-mono: ui-monospace, "SF Mono", "Menlo", Consolas, monospace;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #16140f; --paper: #1d1a14; --ink: #e8e4d8; --ink-soft: #c9c3b3;
    --muted: #8a8474; --rule: #38332a; --rule-strong: #b5ad9b;
    --accent: #e2553a; --accent-soft: #3a1e16;
    --ok: #8cbf8c; --ok-bg: #1e2f1f;
    --warn: #d3aa3c; --warn-bg: #2e2412;
    --fail: #e36758; --fail-bg: #2e1612;
    --info: #87b1d1; --info-bg: #102230;
  }
}
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
body {
  background: var(--bg);
  background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='200' height='200'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' stitchTiles='stitch'/><feColorMatrix values='0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 0.04 0'/></filter><rect width='100%25' height='100%25' filter='url(%23n)'/></svg>");
  color: var(--ink);
  font: 16px/1.65 var(--font-body);
  font-feature-settings: "kern", "liga", "calt", "onum";
  -webkit-font-smoothing: antialiased;
  text-rendering: optimizeLegibility;
}
.container { max-width: 880px; margin: 0 auto; padding: 64px 32px 96px; counter-reset: section; }
.report-banner { border-top: 4px solid var(--accent); border-bottom: 1px solid var(--rule); padding: 24px 0 28px; margin-bottom: 48px; }
.report-banner .kicker { font-family: var(--font-mono); font-size: 11px; letter-spacing: 0.2em; text-transform: uppercase; color: var(--accent); font-weight: 600; margin-bottom: 12px; display: block; }
.report-banner h1 { font-family: var(--font-display); font-variation-settings: "opsz" 96, "wght" 600; font-size: clamp(34px, 5vw, 52px); line-height: 1.08; letter-spacing: -0.015em; margin: 0 0 16px; color: var(--ink); }
.report-banner .subtitle { font-family: var(--font-mono); font-size: 12px; color: var(--muted); letter-spacing: 0.02em; }
.report-banner .subtitle code { background: none; padding: 0; color: var(--ink-soft); border: none; }

nav.toc { margin: 0 0 56px; padding: 20px 24px; background: var(--paper); border-left: 2px solid var(--accent); }
nav.toc > strong { font-family: var(--font-mono); font-size: 10px; letter-spacing: 0.2em; text-transform: uppercase; color: var(--muted); display: block; margin-bottom: 8px; font-weight: 600; }
nav.toc ul { list-style: none; margin: 0; padding: 0; counter-reset: toc; }
nav.toc li { counter-increment: toc; padding: 6px 0; display: flex; align-items: baseline; gap: 16px; }
nav.toc li::before { content: counter(toc, decimal-leading-zero); font-family: var(--font-mono); font-size: 11px; color: var(--accent); font-weight: 600; flex: 0 0 22px; }
nav.toc a { color: var(--ink); text-decoration: none; font-size: 16px; border-bottom: 1px dotted transparent; transition: border-color .18s ease; }
nav.toc a:hover { border-bottom-color: var(--accent); }

section { padding: 56px 0 16px; border-top: 1px solid var(--rule); scroll-margin-top: 24px; animation: au-rise 700ms cubic-bezier(.16,1,.3,1) backwards; }
section:nth-of-type(1) { animation-delay: 0ms; }
section:nth-of-type(2) { animation-delay: 80ms; }
section:nth-of-type(3) { animation-delay: 160ms; }
section:nth-of-type(4) { animation-delay: 240ms; }
section:nth-of-type(5) { animation-delay: 320ms; }
section:nth-of-type(6) { animation-delay: 400ms; }
section:nth-of-type(7) { animation-delay: 480ms; }
section:nth-of-type(8) { animation-delay: 560ms; }
@keyframes au-rise { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }
section > h2 { font-family: var(--font-display); font-variation-settings: "opsz" 48, "wght" 600; font-size: clamp(28px, 3.6vw, 38px); line-height: 1.15; letter-spacing: -0.012em; margin: 0 0 28px; display: flex; align-items: baseline; gap: 22px; }
section > h2::before { counter-increment: section; content: "§" counter(section, decimal-leading-zero); font-family: var(--font-mono); font-size: 12px; letter-spacing: 0.05em; color: var(--accent); font-weight: 600; flex: 0 0 auto; padding-top: 12px; }
h3 { font-family: var(--font-display); font-variation-settings: "opsz" 18, "wght" 600; font-size: 19px; margin: 36px 0 12px; letter-spacing: -0.006em; color: var(--ink); }
h4 { font-family: var(--font-display); font-weight: 600; margin: 24px 0 8px; }
p { margin: 12px 0; }
p.lead { font-family: var(--font-display); font-variation-settings: "opsz" 36, "wght" 500; font-size: clamp(20px, 2.4vw, 24px); line-height: 1.35; color: var(--ink); margin: 8px 0 24px; letter-spacing: -0.005em; }
strong { font-weight: 600; }
em { font-style: italic; }
a { color: var(--accent); text-underline-offset: 3px; text-decoration-thickness: 1px; }
a:hover { text-decoration-thickness: 2px; }
code { font-family: var(--font-mono); font-size: 0.88em; background: var(--paper); padding: 1px 6px; border-radius: 2px; border: 1px solid var(--rule); color: var(--ink-soft); }
pre { font-family: var(--font-mono); background: var(--paper); border: 1px solid var(--rule); border-left: 3px solid var(--accent); padding: 16px 20px; font-size: 13px; line-height: 1.55; overflow-x: auto; margin: 16px 0; }
pre code { background: none; padding: 0; border: 0; }
hr { border: none; border-top: 1px solid var(--rule); margin: 32px 0; }

.table-scroll { overflow-x: auto; margin: 16px 0; }
table { border-collapse: collapse; width: 100%; font-size: 14px; font-family: var(--font-body); font-variant-numeric: tabular-nums oldstyle-nums; }
th, td { text-align: left; vertical-align: top; padding: 12px 16px; border-bottom: 1px solid var(--rule); }
thead th { font-family: var(--font-mono); font-size: 10px; letter-spacing: 0.16em; text-transform: uppercase; color: var(--muted); font-weight: 600; border-bottom: 2px solid var(--rule-strong); padding-bottom: 8px; }
tbody tr { transition: background-color .12s ease; }
tbody tr:hover { background: var(--paper); }
table code { font-size: 12.5px; border: none; background: none; padding: 0; }

.muted { color: var(--muted); font-size: 13px; font-family: var(--font-mono); }
.empty-note { color: var(--muted); font-style: italic; padding: 24px 0; }
ul, ol { padding-left: 24px; margin: 10px 0; }
li { margin: 6px 0; }

/* ---------- README pointer (under banner) ---------- */
.readme-pointer { margin: -32px 0 56px; padding: 14px 20px; background: var(--paper); border-left: 2px solid var(--accent); font-size: 13.5px; color: var(--ink-soft); }

/* ---------- §01 Evals ---------- */
.eval-card { padding: 24px 0 28px; border-bottom: 1px dashed var(--rule); }
.eval-card:last-of-type { border-bottom: none; }
.eval-card-head { display: flex; align-items: baseline; gap: 16px; margin-bottom: 8px; }
.eval-card-head h3 { margin: 0; }
.eval-id { font-family: var(--font-mono); font-size: 11px; letter-spacing: 0.1em; text-transform: uppercase; color: var(--accent); font-weight: 600; }
.eval-desc { color: var(--ink-soft); margin: 8px 0 16px; font-size: 15.5px; }
.eval-prompt-label, .eval-assertions-label { font-family: var(--font-mono); font-size: 10px; letter-spacing: 0.16em; text-transform: uppercase; color: var(--muted); margin-top: 12px; }
.eval-prompt { margin-top: 6px; }
.eval-assertions { list-style: none; padding-left: 0; margin-top: 6px; }
.eval-assertions li { display: flex; gap: 12px; padding: 6px 0; align-items: baseline; }
.kind-tag { font-family: var(--font-mono); font-size: 10px; letter-spacing: 0.1em; text-transform: uppercase; color: var(--muted); padding: 2px 8px; border: 1px solid var(--rule); background: var(--paper); flex: 0 0 auto; }
.assertion-text { font-size: 14.5px; }

/* ---------- §02 Verdict ---------- */
.verdict-hero { border-left: 4px solid var(--accent); padding: 20px 0 20px 24px; margin: 16px 0 0; }
.verdict-kicker { font-family: var(--font-mono); font-size: 10px; letter-spacing: 0.2em; text-transform: uppercase; color: var(--muted); font-weight: 600; }
.verdict-label { font-family: var(--font-display); font-variation-settings: "opsz" 72, "wght" 600; font-size: clamp(28px, 4vw, 40px); line-height: 1.15; letter-spacing: -0.01em; margin: 8px 0 18px; color: var(--accent); }
.verdict-reasoning p { font-size: 16px; line-height: 1.7; color: var(--ink); }
.verdict-hero.verdict-ship .verdict-label { color: var(--ok); }
.verdict-hero.verdict-ship { border-left-color: var(--ok); }
.verdict-hero.verdict-net-negative .verdict-label { color: var(--fail); }
.verdict-hero.verdict-net-negative { border-left-color: var(--fail); }
.verdict-hero.verdict-needs .verdict-label { color: var(--warn); }
.verdict-hero.verdict-needs { border-left-color: var(--warn); }
.verdict-hero.verdict-inconclusive .verdict-label { color: var(--info); }
.verdict-hero.verdict-inconclusive { border-left-color: var(--info); }

/* ---------- §03 Static ---------- */
.static-headline { display: flex; align-items: center; gap: 32px; margin: 24px 0 16px; flex-wrap: wrap; }
.static-score-wrap { display: flex; align-items: baseline; gap: 12px; }
.static-score-label { font-family: var(--font-mono); font-size: 10px; letter-spacing: 0.16em; text-transform: uppercase; color: var(--muted); }
.static-score-value { font-family: var(--font-display); font-variation-settings: "opsz" 96, "wght" 600; font-size: clamp(48px, 6vw, 72px); line-height: 1; letter-spacing: -0.015em; }
.static-score-wrap.score-ok .static-score-value { color: var(--ok); }
.static-score-wrap.score-warn .static-score-value { color: var(--warn); }
.static-score-wrap.score-fail .static-score-value { color: var(--fail); }
.static-side-badges { display: flex; gap: 8px; flex-wrap: wrap; }
.badge { font-family: var(--font-mono); font-size: 11px; letter-spacing: 0.08em; text-transform: uppercase; font-weight: 600; padding: 5px 10px; border: 1px solid; display: inline-block; border-radius: 0; }
.badge.ok   { color: var(--ok);   border-color: var(--ok);   background: var(--ok-bg); }
.badge.warn { color: var(--warn); border-color: var(--warn); background: var(--warn-bg); }
.badge.fail { color: var(--fail); border-color: var(--fail); background: var(--fail-bg); }
.result-cell { font-family: var(--font-mono); font-weight: 600; font-size: 12px; letter-spacing: 0.05em; }
.row-pass .result-cell { color: var(--ok); }
.row-fail .result-cell, .row-fail-hard_fail .result-cell { color: var(--fail); }
.row-fail-warn .result-cell { color: var(--warn); }
.row-fail-info .result-cell { color: var(--info); }
.sev-hard_fail, .sev-warn, .sev-info { font-family: var(--font-mono); font-size: 11px; letter-spacing: 0.08em; text-transform: uppercase; font-weight: 600; }
.sev-hard_fail { color: var(--fail); }
.sev-warn { color: var(--warn); }
.sev-info { color: var(--info); }

/* ---------- §04 Dynamic ---------- */
.metric-grid { display: grid; grid-template-columns: 2.2fr 1.2fr 1.2fr 1fr; gap: 0; margin: 24px 0; border-top: 1px solid var(--rule-strong); border-bottom: 1px solid var(--rule-strong); }
.metric-grid-head, .metric-row { display: contents; }
.metric-grid-head > span { padding: 12px 16px; font-family: var(--font-mono); font-size: 10px; letter-spacing: 0.16em; text-transform: uppercase; color: var(--muted); border-bottom: 1px solid var(--rule); }
.metric-col-label { text-align: right; }
.metric-row > * { padding: 18px 16px; border-bottom: 1px solid var(--rule); }
.metric-row:last-child > * { border-bottom: none; }
.metric-name { font-family: var(--font-body); font-size: 15px; color: var(--ink); }
.metric-val { font-family: var(--font-display); font-variation-settings: "opsz" 24, "wght" 500; font-size: 22px; text-align: right; font-variant-numeric: tabular-nums; }
.metric-val.with { color: var(--ink); }
.metric-val.without { color: var(--muted); }
.metric-val.delta { color: var(--accent); font-weight: 600; }
.config-with_skill { color: var(--ok); font-family: var(--font-mono); font-size: 12px; font-weight: 600; }
.config-without_skill { color: var(--muted); font-family: var(--font-mono); font-size: 12px; }
.diff-list { list-style: none; padding-left: 0; }
.diff-item { padding: 18px 0; border-top: 1px solid var(--rule); display: grid; grid-template-columns: 1fr auto; gap: 8px 24px; align-items: baseline; }
.diff-item:first-child { border-top: none; }
.diff-text { font-size: 15px; color: var(--ink); font-style: italic; }
.diff-meta { font-family: var(--font-mono); font-size: 11px; color: var(--muted); grid-column: 1; }
.diff-rates { display: flex; gap: 16px; grid-row: 1 / span 2; grid-column: 2; }
.diff-rate { font-family: var(--font-display); font-variation-settings: "opsz" 24, "wght" 600; font-size: 20px; }
.diff-rate.diff-with { color: var(--ok); }
.diff-rate.diff-without { color: var(--muted); }

/* ---------- §05 Top fixes ---------- */
.fix-card { padding: 28px 0; border-bottom: 1px solid var(--rule); }
.fix-card:last-of-type { border-bottom: none; }
.fix-card-head { display: flex; align-items: baseline; gap: 16px; margin-bottom: 8px; }
.fix-card-head h3 { margin: 0; font-size: 22px; }
.fix-rank { font-family: var(--font-mono); font-size: 13px; color: var(--accent); font-weight: 600; }
.fix-meta { font-family: var(--font-mono); font-size: 11px; color: var(--muted); margin: 0 0 16px; letter-spacing: 0.04em; }
.fix-prelude { color: var(--ink-soft); margin: 8px 0 16px; }
.fix-block { display: grid; grid-template-columns: 110px 1fr; gap: 20px; padding: 14px 0; border-top: 1px solid var(--rule); }
.fix-block-kicker { font-family: var(--font-mono); font-size: 10px; letter-spacing: 0.2em; text-transform: uppercase; color: var(--muted); padding-top: 4px; }
.fix-block-body p { margin: 0 0 8px; }
.fix-block-body p:last-child { margin-bottom: 0; }
.fix-block.fix-before .fix-block-kicker { color: var(--fail); }
.fix-block.fix-after .fix-block-kicker { color: var(--ok); }
.fix-block.fix-after { background: linear-gradient(90deg, var(--ok-bg) 0%, transparent 24px); }
.fix-block.fix-before { background: linear-gradient(90deg, var(--fail-bg) 0%, transparent 24px); }
.fix-block.fix-problem .fix-block-kicker { color: var(--accent); }
.fix-block.fix-verify .fix-block-kicker { color: var(--info); }
.fix-block.fix-verify .fix-block-body p { font-style: italic; }

/* ---------- §06 Files ---------- */
.file-list { list-style: none; padding-left: 0; }
.file-list li { font-family: var(--font-mono); font-size: 12.5px; padding: 6px 0; border-bottom: 1px dotted var(--rule); color: var(--ink-soft); }
.file-list li code { background: none; border: none; padding: 0; color: inherit; }

/* ---------- Sub-reports (appendix) ---------- */
details { border-top: 1px solid var(--rule); padding: 0; margin: 0; }
details[open] { padding-bottom: 16px; border-bottom: 1px solid var(--rule); }
details + details { margin-top: -1px; }
details > summary { cursor: pointer; padding: 16px 0 16px 32px; position: relative; font-family: var(--font-display); font-variation-settings: "opsz" 18, "wght" 600; font-size: 16px; list-style: none; color: var(--ink); }
details > summary::-webkit-details-marker { display: none; }
details > summary::before { content: ""; position: absolute; left: 0; top: 50%; width: 16px; height: 1px; background: var(--accent); }
details > summary::after  { content: ""; position: absolute; left: 7.5px; top: 50%; margin-top: -7.5px; width: 1px; height: 16px; background: var(--accent); transition: opacity .18s ease; }
details[open] > summary::after { opacity: 0; }
details[open] > summary { color: var(--accent); }

@media (max-width: 720px) {
  .container { padding: 32px 20px 64px; }
  .metric-grid { grid-template-columns: 1fr 1fr; }
  .metric-grid-head > span:first-child { display: none; }
  .metric-row .metric-name { grid-column: 1 / -1; padding-bottom: 4px; color: var(--muted); }
  .fix-block { grid-template-columns: 1fr; gap: 6px; }
  section > h2 { flex-direction: column; gap: 6px; }
  section > h2::before { padding-top: 0; }
}
"""


# ---------------------------------------------------------------------------
# Discovery + main render
# ---------------------------------------------------------------------------


def _read_text(p: Path) -> Optional[str]:
    if not p.is_file():
        return None
    try:
        return p.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _read_json(p: Path) -> Optional[dict]:
    text = _read_text(p)
    if text is None:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _slug(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9_-]+", "-", text.lower()).strip("-")
    return s or "section"


def discover(workspace: Path) -> dict:
    findings: dict = {
        "report_md": _read_text(workspace / "report.md"),
        "static_json": _read_json(workspace / "static.json"),
        "benchmark_json": _read_json(workspace / "benchmark.json"),
        "evals_json": _read_json(workspace / "evals.json"),
        "sub_reports": [],
    }
    for p in sorted(workspace.glob("*.md")):
        if p.name == "report.md":
            continue
        content = _read_text(p)
        if content is None:
            continue
        if re.match(r"^(\d+)[-_](.+)\.md$", p.name):
            findings["sub_reports"].append((p.stem, p, content))
    return findings


def render(workspace: Path, title: str, kicker: Optional[str] = None) -> str:
    findings = discover(workspace)
    report_md = findings["report_md"] or ""
    lang = detect_language(report_md)
    L = LOCALES[lang]
    kicker = kicker or L["report_kicker"]

    sections_md = split_report_sections(report_md)
    verdict_md = sections_md.get("verdict", "")
    fixes_md = sections_md.get("fixes", "")

    body_parts: list[str] = []
    toc: list[tuple[str, str]] = []

    body_parts.append(render_evals(findings["evals_json"], lang))
    toc.append(("evals", L["section_titles"]["evals"]))

    body_parts.append(render_verdict(verdict_md, lang))
    toc.append(("verdict", L["section_titles"]["verdict"]))

    body_parts.append(render_static_section(findings["static_json"], lang))
    toc.append(("static", L["section_titles"]["static"]))

    body_parts.append(render_dynamic_section(findings["benchmark_json"], lang))
    toc.append(("dynamic", L["section_titles"]["dynamic"]))

    body_parts.append(render_top_fixes(fixes_md, lang))
    toc.append(("fixes", L["section_titles"]["fixes"]))

    body_parts.append(render_files_section(workspace, lang))
    toc.append(("files", L["section_titles"]["files"]))

    sub_reports_html = render_sub_reports(findings["sub_reports"], lang)
    if sub_reports_html:
        body_parts.append(sub_reports_html)
        toc.append(("sub-reports", L["section_titles"]["sub_reports"]))

    toc_html = ""
    if toc:
        toc_items = "\n".join(f'<li><a href="#{anchor}">{html.escape(label)}</a></li>' for anchor, label in toc)
        toc_html = f'<nav class="toc"><strong>Contents</strong><ul>{toc_items}</ul></nav>'

    html_lang = "ja" if lang == "ja" else "en"
    return f"""<!DOCTYPE html>
<html lang="{html_lang}">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>{html.escape(title)}</title>
{HEAD_EXTRAS}
<style>{CSS}</style>
</head>
<body>
<div class="container">
<header class="report-banner">
<span class="kicker">{html.escape(kicker)}</span>
<h1>{html.escape(title)}</h1>
<div class="subtitle">workspace: <code>{html.escape(str(workspace))}</code></div>
</header>
<div class="readme-pointer">{html.escape(L["readme_pointer"])}</div>
{toc_html}
{chr(10).join(body_parts)}
</div>
</body>
</html>
"""


def serve(serve_dir: Path, port: int, entry: str, open_browser: bool) -> int:
    """Start a local HTTP server on 127.0.0.1 rooted at serve_dir."""
    handler_cls = partial(http.server.SimpleHTTPRequestHandler, directory=str(serve_dir))

    httpd: Optional[http.server.ThreadingHTTPServer] = None
    bound_port = 0
    for candidate in range(port, port + 20):
        try:
            httpd = http.server.ThreadingHTTPServer(("127.0.0.1", candidate), handler_cls)
            bound_port = candidate
            break
        except OSError:
            continue
    if httpd is None:
        print(f"ERROR: could not bind to any port in {port}..{port + 19}", file=sys.stderr)
        return 3

    url = f"http://127.0.0.1:{bound_port}/{entry}"
    print(f"Serving {serve_dir} at {url}")
    print("Press Ctrl+C to stop.")
    if open_browser:
        webbrowser.open(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nshutting down")
    finally:
        httpd.server_close()
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0] if __doc__ else "render skill-eval workspace to HTML")
    ap.add_argument("workspace", help="Path to skill-eval workspace (typically iteration-N/)")
    ap.add_argument("--out", default=None, help="Output HTML path (default: <workspace>/report.html)")
    ap.add_argument("--title", default=None, help="HTML page title (default: derived from workspace dir)")
    ap.add_argument("--open", action="store_true", help="Open the resulting HTML in the default browser")
    ap.add_argument("--serve", action="store_true", help="Serve via a local HTTP server on 127.0.0.1 (blocks)")
    ap.add_argument("--port", type=int, default=8765, help="HTTP server port (default 8765; auto-fallback +0..+19)")
    args = ap.parse_args()

    workspace = Path(args.workspace).resolve()
    if not workspace.is_dir():
        print(f"ERROR: {workspace} is not a directory", file=sys.stderr)
        return 2

    out_path = Path(args.out).resolve() if args.out else workspace / "report.html"
    title = args.title or f"skill-eval report — {workspace.name}"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render(workspace, title), encoding="utf-8")
    print(f"wrote {out_path}")

    if args.serve:
        return serve(out_path.parent, args.port, out_path.name, open_browser=args.open)
    if args.open:
        webbrowser.open(out_path.as_uri())
    return 0


if __name__ == "__main__":
    sys.exit(main())

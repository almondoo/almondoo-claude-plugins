#!/usr/bin/env python3
"""Static structural quality check for a Claude Code skill.

Reads a target skill directory (containing SKILL.md) and emits static.json
with per-axis pass/fail + evidence, an overall score in [0, 1], and a
hard_fail flag.

Usage:
  python3 static_check.py <target_skill_dir> [--out static.json]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

try:
    import yaml  # type: ignore[import-not-found]
    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False


@dataclass
class Check:
    axis: str
    passed: bool
    severity: str  # "hard_fail" | "warn" | "info"
    evidence: str


FRONTMATTER_RE = re.compile(r"^---\s*\r?\n(.*?)\r?\n---\s*\r?\n", re.DOTALL)
TRIGGER_HINT_RE = re.compile(
    r"\b(when|use(?:\s+this)?|whenever|if|before|after|while|trigger)\b",
    re.IGNORECASE,
)
MUST_NEVER_RE = re.compile(r"\b(MUST|NEVER|ALWAYS)\b")
CODE_FENCE_RE = re.compile(r"^(```|~~~)")
INLINE_CODE_RE = re.compile(r"`[^`\n]+`")

# Narrow emoji range — explicit Emoji blocks only.
# Deliberately excludes U+2600-27BF (Misc Symbols / Dingbats / Misc Technical)
# because that range contains common technical symbols like → ✓ ✗ ★ ⇒ that
# appear in well-written prose. False negatives (missing ⚠ / ⏰ etc.) are
# preferred over false positives on otherwise-clean skills.
EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001F9FF"  # Misc Symbols & Pictographs, Emoticons, Transport, Supplemental
    "\U0001FA00-\U0001FAFF"  # Symbols and Pictographs Extended-A
    "]"
)


def strip_code(text: str) -> str:
    """Remove fenced code blocks (``` or ~~~) and inline code spans so
    meta-mentions of MUST/NEVER (e.g. when explaining anti-patterns) are
    not counted as actual enforcement uses."""
    out: list[str] = []
    in_fence = False
    fence_char: Optional[str] = None
    for line in text.splitlines():
        stripped_line = line.strip()
        m = CODE_FENCE_RE.match(stripped_line)
        if m:
            tok = m.group(1)
            if not in_fence:
                in_fence = True
                fence_char = tok
            elif tok == fence_char:
                in_fence = False
                fence_char = None
            continue
        if in_fence:
            continue
        out.append(INLINE_CODE_RE.sub("", line))
    return "\n".join(out)


def _strip_quotes(v: str) -> str:
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in ('"', "'"):
        return v[1:-1]
    return v


def parse_frontmatter(text: str) -> tuple[Optional[dict], str]:
    """Parse YAML frontmatter. Uses PyYAML when available, otherwise falls
    back to a hardened minimal parser that handles CRLF, quotes, and
    block scalars (`|` / `>`)."""
    # Normalize line endings up front so the regex always works.
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None, text
    raw = m.group(1)
    body = text[m.end():]

    if _HAS_YAML:
        try:
            parsed = yaml.safe_load(raw) or {}
            if isinstance(parsed, dict):
                # Coerce values to strings for downstream comparison.
                return ({str(k): str(v) for k, v in parsed.items()}, body)
        except yaml.YAMLError:
            pass  # fall through to minimal parser

    fm: dict[str, str] = {}
    current_key: Optional[str] = None
    block_mode: Optional[str] = None  # "|" or ">" if inside block scalar
    for line in raw.splitlines():
        # Block-scalar continuation: indented line after a `key: |` / `key: >`
        if block_mode and current_key and (line.startswith(" ") or not line.strip()):
            content = line.strip()
            sep = "\n" if block_mode == "|" else " "
            fm[current_key] = (fm.get(current_key, "") + sep + content).strip()
            continue
        block_mode = None
        if ":" in line and not line.startswith(" "):
            k, _, v = line.partition(":")
            current_key = k.strip()
            v = v.strip()
            if v in ("|", ">"):
                block_mode = v
                fm[current_key] = ""
            else:
                fm[current_key] = _strip_quotes(v)
        elif current_key and line.startswith(" "):
            # Folded continuation line for an inline-started value
            fm[current_key] = (fm.get(current_key, "") + " " + line.strip()).strip()
    return fm, body


def check_frontmatter(fm: Optional[dict], dir_name: str) -> list[Check]:
    out: list[Check] = []
    if fm is None:
        out.append(Check(
            axis="frontmatter.present",
            passed=False,
            severity="hard_fail",
            evidence="No YAML frontmatter block found at top of SKILL.md",
        ))
        return out
    name = (fm.get("name") or "").strip()
    desc = (fm.get("description") or "").strip()
    # Per https://code.claude.com/docs/en/skills.md frontmatter reference:
    # "If omitted, uses the directory name." — explicit mismatch is also
    # legal (it sets a stable invocation name independent of install path).
    # So name/dir mismatch is a `warn`, not a `hard_fail`.
    if not name:
        out.append(Check(
            axis="frontmatter.name_matches_dir",
            passed=True,
            severity="warn",
            evidence=f"name omitted, will fall back to dir basename {dir_name!r} (legal per spec)",
        ))
    else:
        out.append(Check(
            axis="frontmatter.name_matches_dir",
            passed=name == dir_name,
            severity="warn",
            evidence=f"name={name!r}, dir={dir_name!r} ({'match' if name == dir_name else 'mismatch — legal but unusual; intentional only for stable invocation across install paths'})",
        ))
    out.append(Check(
        axis="frontmatter.description_present",
        passed=bool(desc),
        severity="hard_fail",
        evidence=f"description length: {len(desc)} chars",
    ))
    out.append(Check(
        axis="frontmatter.description_has_trigger",
        passed=bool(TRIGGER_HINT_RE.search(desc)),
        severity="warn",
        evidence="contains when/use/trigger hint" if TRIGGER_HINT_RE.search(desc) else "no trigger hint detected",
    ))
    desc_ok = 50 <= len(desc) <= 1536
    out.append(Check(
        axis="frontmatter.description_length",
        passed=desc_ok,
        severity="warn",
        evidence=f"{len(desc)} chars (Anthropic caps description + when_to_use combined at 1536; lower bound 50 is community heuristic)",
    ))
    return out


def check_body(body: str) -> list[Check]:
    out: list[Check] = []
    lines = body.splitlines()
    n = len(lines)
    out.append(Check(
        axis="body.line_count",
        passed=n <= 500,
        severity="warn",
        evidence=f"{n} lines (recommended <= 500)",
    ))
    stripped = strip_code(body)
    must_count = len(MUST_NEVER_RE.findall(stripped))
    density = (must_count / max(n, 1)) * 100
    out.append(Check(
        axis="body.must_never_density",
        passed=density <= 10,
        severity="warn",
        evidence=f"{must_count} MUST/NEVER/ALWAYS occurrences in {n} lines (density {density:.1f}/100 lines, excluding code spans)",
    ))
    emoji_matches = EMOJI_RE.findall(stripped)
    out.append(Check(
        axis="body.no_emoji",
        passed=not emoji_matches,
        severity="warn",
        evidence=(
            f"found emoji characters: {sorted(set(emoji_matches))[:5]} (range U+1F300-1FAFF; technical symbols → ✓ ★ are intentionally NOT flagged)"
            if emoji_matches
            else "no emoji in body (excluding code spans)"
        ),
    ))
    return out


def check_structure(skill_dir: Path, body: str) -> list[Check]:
    out: list[Check] = []
    refs = skill_dir / "references"
    scripts = skill_dir / "scripts"
    assets = skill_dir / "assets"
    has_pd = any(p.is_dir() for p in (refs, scripts, assets))
    out.append(Check(
        axis="structure.has_progressive_disclosure",
        passed=has_pd,
        severity="info",
        evidence=f"references={refs.is_dir()} scripts={scripts.is_dir()} assets={assets.is_dir()}",
    ))
    for sub, axis in ((scripts, "structure.scripts_referenced_from_body"), (refs, "structure.references_referenced_from_body")):
        if not sub.is_dir():
            continue
        unreferenced = []
        for p in sub.iterdir():
            if p.is_file() and p.name not in body:
                unreferenced.append(p.name)
        out.append(Check(
            axis=axis,
            passed=not unreferenced,
            severity="warn",
            evidence=(f"unreferenced files: {unreferenced}" if unreferenced else "all referenced"),
        ))
    return out


def score(checks: list[Check]) -> tuple[float, bool, int]:
    """Compute weighted score in [0, 1]. If any `hard_fail`-severity check
    fails, the result is capped at 0.4 (below the "Needs work" verdict
    threshold) so that ship-blocker conditions cannot produce a high
    overall score."""
    hard_failed = False
    weighted_total = 0.0
    weighted_max = 0.0
    warnings = 0
    weights = {"hard_fail": 3.0, "warn": 1.0, "info": 0.3}
    for c in checks:
        w = weights[c.severity]
        weighted_max += w
        if c.passed:
            weighted_total += w
        else:
            if c.severity == "hard_fail":
                hard_failed = True
            elif c.severity == "warn":
                warnings += 1
    raw = (weighted_total / weighted_max) if weighted_max else 0.0
    s = min(raw, 0.4) if hard_failed else raw
    return s, hard_failed, warnings


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("target", help="Path to skill directory containing SKILL.md")
    ap.add_argument("--out", default=None, help="Output JSON path (default: stdout)")
    args = ap.parse_args()

    target = Path(args.target).resolve()
    skill_md = target / "SKILL.md"
    if not skill_md.is_file():
        print(f"ERROR: {skill_md} not found", file=sys.stderr)
        return 2

    text = skill_md.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(text)
    checks: list[Check] = []
    checks.extend(check_frontmatter(fm, target.name))
    checks.extend(check_body(body))
    checks.extend(check_structure(target, body))
    s, hard_failed, warnings = score(checks)

    result = {
        "target": str(target),
        "score": round(s, 3),
        "hard_fail": hard_failed,
        "warnings": warnings,
        "checks": [asdict(c) for c in checks],
    }
    payload = json.dumps(result, indent=2, ensure_ascii=False)
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(payload, encoding="utf-8")
        print(f"wrote {out_path} (score={result['score']}, hard_fail={result['hard_fail']}, warnings={result['warnings']})")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())

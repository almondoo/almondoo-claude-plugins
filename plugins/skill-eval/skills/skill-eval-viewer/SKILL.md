---
name: skill-eval-viewer
description: Render a skill-eval workspace (iteration directory containing report.md / static.json / benchmark.json / NN-*.md sub-reports) into a single self-contained HTML file. Use whenever the user wants to view a skill-eval evaluation result as a webpage, share a report visually, read multi-angle subagent reports side-by-side, or serve the report via http://localhost.
---

# skill-eval-viewer

Companion skill to [`skill-eval`](../skill-eval/). After `skill-eval` produces an `iteration-N/` workspace (report.md + static.json + benchmark.json + NN-*.md sub-reports), this skill renders that workspace into a designed HTML report and optionally serves it on `http://127.0.0.1:PORT/`.

Design: **"Field Audit"** — editorial engineering. Fraunces variable serif display + system serif body + system mono. Bone paper, vermillion accent, numbered sections, hairline rules, paper grain background. Light / dark theme follows the OS via `prefers-color-scheme`.

---

## When to use

- Right after running `skill-eval` and the markdown report has many tables / sub-reports awkward to read in a plain editor.
- When sharing an evaluation summary with someone who prefers a webpage to raw markdown.
- When multiple subagent reports (e.g. `01-official-spec.md`, `02-skill-creator-alignment.md`, ...) need to be compared side-by-side as collapsible sections.

This skill **only renders**. It does not run evaluations. Run [`skill-eval`](../skill-eval/) first to produce the workspace, then invoke this skill.

---

## Inputs

Collect via `AskUserQuestion`, skipping whatever the user has already provided:

1. **workspace_dir** (required) — directory to render. Typically an `iteration-N/` subdirectory produced by `skill-eval`. Any directory containing `report.md` / `static.json` / `benchmark.json` / `NN-*.md` is accepted.
2. **out_path** (optional) — output HTML path. Default: `<workspace_dir>/report.html`.
3. **delivery mode** (optional) — one of:
   - **`file`** (default) — write the HTML and stop. The user opens it themselves (or pass `--open` to launch the default browser via `file://`).
   - **`serve`** — write the HTML and start a local HTTP server on `127.0.0.1:8765` (auto-fallback through port+19 if 8765 is in use). Use this when the user prefers an `http://localhost:...` URL — easier to bookmark, share within the same machine, and avoids browser quirks around `file://` permissions. Blocks the script until `Ctrl+C`, so launch via Bash with `run_in_background: true`. **Scope note**: the server roots at the directory containing `report.html` (the workspace, or `--out`'s parent). Every file directly under that directory becomes readable on `127.0.0.1` while the server runs. Loopback binding keeps it off the LAN, but any process on the same machine can read whatever you place there — keep transient logs / secrets out of the workspace before serving.

---

## What the script discovers

The renderer walks the workspace once and looks for these artifacts (all optional):

| File pattern | Section | How it renders |
|---|---|---|
| `report.md` | **Overview** (expanded) | Markdown → HTML; the front page |
| `static.json` | **Static layer** | Score badges + per-axis table with severity coloring |
| `benchmark.json` | **Dynamic layer** | with/without/delta summary + per-eval table + differentiating assertions |
| `NN-*.md` (numbered prefix) | **Multi-angle sub-reports** | Each in a `<details>` block, sorted by NN |
| Other `*.md` | **Other documents** | Fallback `<details>` blocks for anything else |

Missing files are skipped silently. A workspace with **only** `report.md` still renders fine.

The script knows the skill-eval JSON shapes (`score` / `hard_fail` / `checks[]` for static, `run_summary` / `runs[]` / `differentiating_assertions[]` for benchmark) and applies typed rendering.

---

## Running it

```bash
python3 <this-skill-path>/scripts/render_html.py <workspace_dir> \
  [--out <path>] [--title "..."] [--open] [--serve [--port N]]
```

Examples:

```bash
# Write report.html and stop. Chrome language is auto-detected from report.md.
python3 .../scripts/render_html.py tmp/skill-eval-evaluation/iteration-1/

# Open the file:// URL after writing
python3 .../scripts/render_html.py tmp/foo-evaluation/iteration-2/ \
  --title "foo skill — iteration 2" --open

# Serve via http://127.0.0.1:8765/report.html and auto-open the browser.
# Bind to loopback only — never exposed to the LAN.
python3 .../scripts/render_html.py tmp/skill-eval-evaluation/iteration-1/ \
  --serve --port 8765 --open
```

**Chrome language is driven by `report.md`'s content.** The renderer inspects the first ~400 characters and picks `ja` if CJK ≥ 25%, otherwise `en`. The orchestrating skill (`skill-eval`) is expected to have already used `AskUserQuestion` to confirm the language with the user **before writing `report.md`** — so by the time this viewer runs, `report.md` is already in the target language and the auto-detect simply mirrors it. There is no `--lang` flag; the markdown is the source of truth.

When invoking from Claude Code with `--serve`, launch via the Bash tool with `run_in_background: true` so the server keeps running while Claude continues. Stop it via the background task stop facility when no longer needed.

`<this-skill-path>` resolves to the directory containing this `SKILL.md`. When invoking via Claude Code, use the absolute path Claude resolves at load time.

---

## How the HTML looks

- **Banner** with kicker label ("SKILL EVALUATION REPORT"), title, and workspace path. Top edge is a 4px vermillion rule.
- **Table of contents** in a paper-toned card with left vermillion border and mono-numeric prefixes.
- **Numbered sections** — each `<h2>` is preceded by a mono `01` / `02` / `03` counter generated via CSS counters.
- **Static layer**: three badges (`score`, `hard_fail`, `warnings`) + a per-axis table with color-coded `severity` (red = `hard_fail`, yellow = `warn`, blue = `info`).
- **Dynamic layer**: summary table with `mean ± stddev` cells when stddev is non-zero, per-eval breakdown, and differentiating assertions if any.
- **Multi-angle sub-reports**: each `NN-*.md` rendered inside a `<details>` block. The summary toggles a plus / minus glyph drawn from CSS pseudo-elements.
- **Light/dark theme** follows the OS (`prefers-color-scheme`).
- **Motion**: each section fades up with staggered delays (90ms apart) on initial paint.

---

## Workflow

1. Confirm `workspace_dir`, `out_path`, and **delivery mode** (`file` vs `serve`) via `AskUserQuestion`. Language is not asked here — it is set by `report.md` content, which the orchestrating `skill-eval` already finalized.
2. Run `render_html.py` (Bash). For `serve` mode use `run_in_background: true` so the server does not block.
3. Report the absolute path of the output file, and — in `serve` mode — the `http://127.0.0.1:PORT/report.html` URL plus the background task id that can stop it.

---

## Edge cases

- **Workspace has no recognized artifacts** — the page renders with a single "No recognized artifacts found" note. Tell the user to point at a different directory (often they passed the parent of `iteration-N/`).
- **`benchmark.json` exists but is malformed** — silently skipped (rendered as if absent). Surface this to the user only if they ask why the Dynamic section is missing.
- **`report.md` contains an embedded HTML block** — the markdown renderer escapes everything; raw HTML is shown as text. This is intentional: report files come from untrusted subagents, and we don't want script-injection.
- **Very large `report.md` (>500 KB)** — still works, but the resulting HTML is a single file and the browser will load it all at once. If this becomes a real friction point, split the report into `NN-*.md` sub-files so they render as collapsible sections instead.
- **`--serve` port collision** — the script tries `--port` first, then increments through `+19` to find a free port (`port..port+19`, 20 candidates total). The chosen port is printed. If all 20 are occupied the script exits with code 3 — pass an explicit `--port` higher in the ephemeral range.
- **Offline / Google Fonts blocked** — Fraunces falls back to `ui-serif` / Charter / Georgia. Layout works; only the display headline character shifts.

---

## Design notes

- **Single-purpose**: rendering is mechanical and doesn't need an LLM. Keeping it in a script (not an agent) lets it run deterministically with zero token spend.
- **Stdlib-only Python**: the markdown→HTML pass is regex-based on purpose. Pulling in `markdown` / `markdown-it` would force users to install Python packages just to view a report. The cost is that exotic markdown (footnotes, math, deep blockquotes) is not supported — but skill-eval reports don't use those.
- **No client JS**: motion is CSS keyframes; collapsing is native `<details>`. Works offline, in restricted environments, can be archived.
- **One Google Fonts link (Fraunces)** is the single external dependency. System-font fallbacks keep the page legible if the CDN fails. The trade-off: typographic identity > zero-dep purity.
- **Sibling skill to `skill-eval`, not bundled into it**: `skill-eval` writes JSON + markdown as machine artifacts; this skill is the human-facing viewer. Both ship under the same plugin (`skill-eval`), so installing the plugin gets both capabilities — but they trigger independently so the user can view an existing workspace without re-running an evaluation.

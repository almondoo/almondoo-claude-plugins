---
name: skill-eval
description: Evaluate a Claude Code skill on two layers — structural quality (frontmatter validity, body length, progressive disclosure, description triggerability) and practical effectiveness (run the same prompts with-skill vs without-skill in parallel subagents and compare pass rate, time, and tokens). Use whenever the user wants to know "does this skill actually help", needs to audit a skill for claude-code plugin convention compliance before shipping, wants to benchmark with-skill against without-skill on real prompts, or needs to measure whether one skill version is better than another.
---

# skill-eval

Evaluate any Claude Code skill on **two layers — static + dynamic** and emit both a human-readable report and a machine-readable JSON.

The evaluation target is a directory that contains a single `SKILL.md`. Either a standalone skill directory or a per-plugin skill directory (`skills/*` under a `.claude-plugin/plugin.json`) is accepted.

---

## Why two layers

- **Static alone** misses the "well-written but useless in practice" skill.
- **Dynamic alone** misclassifies a skill as "good" when the LLM happened to push through on that particular run — and the result fails to reproduce in someone else's environment. Structural debt (body too long, over-imperative tone, no progressive disclosure) is also invisible to the execution benchmark.
- Producing both lets the judge demand "structurally sound AND measurably with > without" before shipping.

The axis details live in `references/eval-axes.md`. The thesis that "a skill should explain *why* instead of leaning on `MUST` / `NEVER`" aligns with the claude-code-plugin convention (the "Writing Style" section in Anthropic's `skill-creator` skill).

---

## Step 0: Plan the iteration as a task list

Before touching any tool, call `TaskCreate` and break the iteration into one task per step (Step 1 static → Step 2 evals → … → Step 6 unified report + HTML). Mark a task `in_progress` when you start it and `completed` when you finish — never batch the status updates. The task list is the visible progress signal for the user; the steps below are long, the harness shows only your messages and tool calls, and silent gaps are easy to misread as a stall.

Suggested initial set (adjust to inputs once collected):

- Step 1 — static_check.py
- Step 2 — confirm evals.json
- Step 3 — dispatch A/B subagents
- Step 4 — grade
- Step 5 — aggregate benchmark.json
- Step 6 — write report.md + render report.html

---

## Inputs

Collect the following from the user (skip whatever has already been provided):

1. **target_skill_path** (required) — directory of the skill to evaluate, e.g. `/path/to/plugins/foo/skills/foo/`. `SKILL.md` must live directly under it.
2. **eval prompts** (optional) — test prompts. If absent, auto-generate 3 from the static result and the SKILL.md description, then confirm. Each eval must carry a one-sentence `description` field explaining what it tests — without it, the HTML report cannot tell the reader why this prompt matters.
3. **runs_per_configuration** (optional) — number of repetitions per A/B configuration. Default 1. Suggest 3 only when you need to measure variance.
4. **skip dynamic?** (optional) — if the user wants static only, skip the dynamic layer.

Ask via AskUserQuestion (do not ask through plain text output).

### Report language

`AskUserQuestion` the user for the report language as one of the Step 0 / Inputs questions. The two supported values are `ja` (Japanese) and `en` (English) — the only entries in the viewer's `LOCALES` table. Default the question to whichever language the user's original prompt was written in, but always surface it explicitly rather than silently inferring it.

Once chosen, write `report.md` in that language. The HTML renderer auto-detects the same language from the markdown content (CJK ≥ 25% → `ja`, else `en`) and matches the chrome accordingly; there is no separate language flag on the renderer because the markdown already encodes the choice.

The eval workspace lives at `tmp/skill-eval/<skill-name>/` under the current working directory — outside the in-repo "write in English" perimeter and outside any installed plugin tree, treated like `tmp/` under the project's language policy. Non-English text is permitted there. Only the headline labels, table column names, and code identifiers stay in their canonical form.

### Placeholders used throughout this skill

The commands and snippets below repeatedly use angle-bracket placeholders. Resolve each at invocation time:

- `<target_skill_path>` — input #1, the directory of the skill being evaluated.
- `<workspace>` — `tmp/skill-eval/<skill-name>/` under the current working directory (`<skill-name>` = directory basename of `<target_skill_path>`). The workspace **must live outside the `plugins/` tree** so it is not distributed when this plugin is installed by another project; `tmp/` is gitignored both here and by convention in user projects.
- `N` — current iteration number, starting at 1 and incrementing per re-run.
- `<this-skill-path>` — the directory containing this `SKILL.md` (the skill-eval skill itself); use the absolute path Claude Code passes at skill-load time.
- `<viewer-skill-path>` — the directory containing the sibling `skill-eval-viewer` skill; resolves to `../skill-eval-viewer/` relative to `<this-skill-path>` in this plugin.

---

## Workflow overview

```
[Step 0] task list — TaskCreate one task per step below
[Step 1] static_check.py scores structure          → static.json
[Step 2] confirm eval prompts (provided or auto-generated; each carries a description)
[Step 3] for each prompt, dispatch with_skill / without_skill subagents
         in parallel within the same turn
[Step 4] grader (agents/grader.md) scores each run against assertions → grading.json
[Step 5] aggregate_benchmark.py emits benchmark.json + benchmark.md
[Step 6] write report.md AND render report.html (viewer skill) — both artefacts in same step
```

The workspace lives at **`tmp/skill-eval/<skill-name>/`** under the current working directory, where `<skill-name>` is the directory basename of `target_skill_path`. This is intentionally outside the `plugins/` tree: when this plugin is installed by another project, the plugin source must not carry per-target evaluation history. `tmp/` is gitignored at the marketplace root and by convention in user projects.

Each run creates a fresh `iteration-N/` subdirectory under the workspace; `N` starts at `1` on first run and increments by `1` for each subsequent run (determined by listing existing `iteration-*` subdirectories and taking the highest N + 1). All Step 1–6 commands in this skill use `<workspace>` to refer to `tmp/skill-eval/<skill-name>/` (the parent of the iteration dirs). The layout mirrors skill-creator's so that the workspace can later be carried into skill-creator for further iteration.

---

## Step 1: Static scoring

Run `scripts/static_check.py`:

```bash
python3 <this-skill-path>/scripts/static_check.py <target_skill_path> \
  --out <workspace>/iteration-N/static.json
```

Axes (1:1 with the implementation; see `references/eval-axes.md` for details):

| Axis | What it checks | Weight |
|---|---|---|
| frontmatter.present | YAML frontmatter block exists at the top of SKILL.md. Added only when frontmatter is missing — replaces every other frontmatter.* axis in that run | hard fail if missing |
| frontmatter.name_matches_dir | `name:` matches the directory name (the official spec treats omission/mismatch as legal, so **warn** only) | warn |
| frontmatter.description_present | description is non-empty | hard fail if missing |
| frontmatter.description_has_trigger | description includes "when to use" cues (verb + context) | warn |
| frontmatter.description_length | The official cap on the `description` field (which embeds when-to-use guidance) is 1,536 chars. The 50-char lower bound is a community heuristic | warn if outside |
| body.line_count | body (after frontmatter) ≤ 500 lines | warn over |
| body.must_never_density | density of `MUST` / `NEVER` / `ALWAYS` (excluding code spans). High ≈ "why" is missing | warn |
| body.no_emoji | no emoji in the body (U+1F300–1FAFF). Technical glyphs (→ ✓ ★ etc.) are exempt | warn |
| structure.has_progressive_disclosure | at least one of references/ scripts/ assets/ exists | info (unnecessary when the body is short — roughly ≤ 100 lines) |
| structure.scripts_referenced_from_body | files under scripts/ are referenced from SKILL.md | warn unreferenced |
| structure.references_referenced_from_body | same for references/ | warn unreferenced |

**hard_fail semantics**: when any axis with severity=`hard_fail` fails, `hard_fail: true` is flagged and the score is capped at 0.4 — below the "Needs work" threshold — so that ship-blocker conditions cannot produce a high overall score.
**When frontmatter is absent**: only `frontmatter.present` (severity=hard_fail) is added; the rest of the frontmatter axes are skipped. The body and structure axes still run.

`static_check.py` writes the scoring to `static.json`, e.g.:

```json
{
  "target": "/path/to/skill",
  "score": 0.82,
  "checks": [
    {"axis": "frontmatter.name_matches_dir", "passed": true, "evidence": "..."},
    {"axis": "body.must_never_density", "passed": false, "evidence": "23 occurrences in 180 lines (>10/100)"}
  ],
  "hard_fail": false,
  "warnings": 2
}
```

If `hard_fail: true`, surface the structural blocker via AskUserQuestion before continuing: present the failing axis evidence and ask whether to (a) fix the blocker first and re-run, (b) skip the dynamic layer and proceed to Step 6 static-only report, or (c) attempt the dynamic layer anyway (advanced — produces likely-meaningless benchmark). Default option (a). The user's `skip dynamic?` input from Step 4 of Inputs is honored as (b) without re-asking if already set.

---

## Step 2: Confirm eval prompts

The source of truth for an evaluation run is **`<workspace>/iteration-N/evals.json`** — every later step reads from there. The target's own `<target_skill_path>/evals/evals.json` (when present) is only a *seed*: this skill never mutates it.

1. **Source check**: if `<target_skill_path>/evals/evals.json` exists, load it as the starting set (skill authors often co-locate canonical evals with their skill). Otherwise generate 3 prompts from the SKILL.md description and body.
2. **Confirm**: present the prompts (adopted or generated) via AskUserQuestion (edit / add / OK).
3. **Persist**: write the confirmed set to `<workspace>/iteration-N/evals.json`. Subsequent steps read this file. The seed file under `<target_skill_path>/evals/` is left untouched, so each iteration can re-seed from it intentionally rather than picking up partial edits.

Prompt-writing guidance (same thesis as skill-creator's "Description Optimization" section — concrete, multi-step, realistic queries beat abstract ones):

- Avoid abstract prompts (`"Format this data"`); use concrete details a real user would type (file name, column name, surrounding context).
- Pick **multi-step / specialized** subjects that show off the skill — one-shot tasks that anyone can solve do not differentiate.
- Mix in one "neighbor task" that the description does not anticipate. This catches over-triggering and misapplication.

Attach 2–4 assertions per prompt:

```json
{
  "evals": [
    {
      "id": 1,
      "name": "extract-table-from-quarterly-pdf",
      "prompt": "Convert Q4 sales final FINAL v2.xlsx to CSV...",
      "assertions": [
        {"text": "output contains a Revenue column", "kind": "factual"},
        {"text": "amounts are stored as a numeric type", "kind": "format"}
      ]
    }
  ]
}
```

---

## Step 3: A/B parallel dispatch

For each eval prompt, launch **two `general-purpose` Agents in parallel within the same turn** (`run_in_background: true`) — one with the skill, one without — and persist `timing.json` (containing `total_tokens` / `duration_ms`) to each `<run-dir>/` **immediately** when the completion notification arrives. The values cannot be retrieved after the notification has passed.

Soft cap = 6 subagents per iteration: when `2 × prompts × runs_per_configuration > 6`, reduce inputs at Step 2 rather than batching across turns — batching breaks cross-eval comparability (time-of-day, model load) which is the entire reason same-turn dispatch exists.

Full subagent prompt templates, safety check (warn for skills that perform external writes), and notification-handling rationale: see [`references/step-3-dispatch.md`](references/step-3-dispatch.md).

---

## Step 4: Grading

Spawn one grader subagent per run. Each grader reads `<this-skill-path>/agents/grader.md` (a frontmatter-less prompt template, not a dispatchable Claude Code agent file) and applies it to that run's outputs against the assertions from `evals.json`, writing `grading.json` to the run directory.

`grading.json` field names — `expectations[] / text / passed / evidence / summary` — are read by key in the aggregator and viewer; **do not rename them**. The input/output schema asymmetry (`assertions: [{text, kind}]` in `evals.json` → `expectations: [{text, passed, evidence}]` in `grading.json`) is intentional.

Full grader input shape, programmatic vs. eyeball verification guidance, and asymmetry rationale: see [`references/step-4-grading.md`](references/step-4-grading.md).

---

## Step 5: Aggregation

```bash
python3 <this-skill-path>/scripts/aggregate_benchmark.py \
  <workspace>/iteration-N \
  --skill-name <target-skill-name> \
  --out <workspace>/iteration-N/benchmark.json
```

The script emits `benchmark.json` plus `benchmark.md`. Load-bearing top-level keys (read by the viewer in this order): `metadata` / `runs[]` / `run_summary` / `differentiating_assertions[]` / `notes[]`. The schema mirrors skill-creator's reference so the same viewer can render it.

`stddev` is `null` when `n < 2` (single-sample and all-equal must not collide); missing measurements (`time_seconds: null` for a run without `timing.json`) are excluded from `mean` / `stddev` rather than counted as zero — `_cell()` renders them as `"n/a (N missing)"`.

Full per-key schema, sample markdown layout, and missing-data semantics: see [`references/step-5-aggregation.md`](references/step-5-aggregation.md).

---

## Step 6: Unified report — markdown AND HTML

Step 6 produces both artifacts in the same step. The markdown is the source of truth (the renderer parses it for verdict / top-fix narrative); the HTML is the human-facing deliverable. Generate them in this order on the same turn.

### 6a. Scaffold and hand-write `report.md`

`scripts/render_report.py` scaffolds `report.md` from `static.json` and `benchmark.json`:

```bash
python3 <this-skill-path>/scripts/render_report.py \
  --static <workspace>/iteration-N/static.json \
  --benchmark <workspace>/iteration-N/benchmark.json \
  --out <workspace>/iteration-N/report.md
```

`--benchmark` is optional (omitting it produces a static-only report). After scaffolding, hand-write the verdict and the top fix candidates **in the language of the user's original prompt**. The Top-fix section follows the four-block before/after schema (`problem / before / after / verify`) defined in [`references/proposal-derivation.md`](references/proposal-derivation.md) §5.

### 6b. Render `report.html`

Hand off to the sibling [`skill-eval-viewer`](../skill-eval-viewer/) skill to render the workspace into a single self-contained HTML report:

```bash
python3 <viewer-skill-path>/scripts/render_html.py <workspace>/iteration-N/ \
  --title "skill-eval report: <target-skill-name> (iteration-N)"
```

**Confirm the report language with the user via `AskUserQuestion` before Step 6a**. The two supported chrome languages are `ja` and `en` (the only entries in the viewer's `LOCALES` table). Write `report.md` in the language the user chooses; the viewer auto-detects the same language from `report.md` content and matches the chrome (section titles, verdict labels, before/after kickers, README pointer). The renderer carries no `--lang` flag — the markdown is the source of truth.

This is **part of Step 6**, not an optional follow-up. The HTML adds per-eval description / verdict hero / before-after fix cards that the markdown does not carry, and is the form most users will actually read. Add `--open` if the user wants the browser launched; add `--serve` (with `run_in_background: true`) if they want a localhost URL to share.

Design contract for the HTML (six numbered sections — evals, verdict, static, dynamic, top fixes, files; plugin overview / glossary live in the README, not the report): see `<viewer-skill-path>/references/frontend-design.md`.

Minimal manual format:

```markdown
# skill-eval report: <skill-name>

## Verdict
<one-liner; pick exactly one: `Ship-ready` / `Needs work` / `Net negative` / `Inconclusive`>

## Static (score: <0.0-1.0> / hard_fail: <true|false>)
- bullet pass/fail with evidence per axis

## Dynamic
| metric | with_skill | without_skill | Δ |
| pass_rate | 0.83 | 0.33 | +0.50 |
| time (s) | 42.5 | 32.0 | +10.5 |
| tokens | 3800 | 2100 | +1700 |

## Differentiating assertions
- each differentiating assertion text with (eval_name, with_rate, without_rate)

## Top issues to fix
1. (up to 3 items — derivation guidance in `references/proposal-derivation.md`)

## Files
- static.json / benchmark.json / runs/eval-*/{with_skill,without_skill}/outputs/
```

### Top issues to fix — derivation

The scaffold placeholder requires hand-writing. The Category × Priority schema (inherited from skill-creator `agents/analyzer.md`) plus the perspectives and examples specific to skill-eval are consolidated in [`references/proposal-derivation.md`](references/proposal-derivation.md). The essentials:

- **Draw from four sources**: (a) static FAIL / warn, (b) the flip side of differentiating assertions (`with-only-pass` = a contract to codify; `without-only-pass` = mis-steering to remove), (c) anomalies such as `time ≥ 2×` or `variance > mean × 0.3`, (d) dogfooding gap (axes static_check does not cover: writing quality / placeholder resolution / translation ambiguity / internal consistency / script↔doc drift).
- **Priority is judged by outcome-changing** — not by effort or subjective importance. The only condition for `high` is: "Without this fix, would the next iteration's benchmark numbers (pass_rate / verdict / differentiating count) have moved?"
- **At most 3 items**. More invites overfit and cognitive load and makes it impossible to isolate which fix actually worked. The remainder is deferred to the open follow-ups list in `LEARNINGS.md`.

For each fix, always fill in: category (`instructions / tools / examples / error_handling / structure / references`), source (one of the four), and verifiability (a measurable hypothesis for the next iteration).

Verdict heuristics — evaluate in this order, first match wins (the order resolves boundary overlaps). The user makes the final call:

- **Net negative**: `pass_rate delta < 0`, OR (`time ≥ 2×` AND `tokens ≥ 2×`). A *negative* delta means with-skill scored worse than without — actionable harm. `delta = 0` is "the skill did nothing" which is wasteful but not actively harmful; it falls into Needs work below.
- **Ship-ready**: `static score ≥ 0.8` AND `pass_rate delta ≥ +0.2`
- **Needs work**: any case not caught above (covers `static score 0.4–0.8`, `pass_rate delta` in `[0, +0.2)`, etc.)
- **Inconclusive** (variance flag, additive — does not displace the above): `runs_per_configuration ≥ 3` AND `stddev > mean × 0.3`. When `runs_per_configuration < 3`, append "single-run, variance not measured" to the report but assign the verdict from the first three rules.

---

## Step 7 (optional): serve the HTML on localhost

The HTML file is already rendered in Step 6b. Step 7 only exists when the user wants `http://127.0.0.1:PORT/report.html` (easier to bookmark / share / inspect with browser devtools than `file://`).

```bash
python3 <viewer-skill-path>/scripts/render_html.py <workspace>/iteration-N/ --serve --port 8765
```

Launch via the Bash tool with `run_in_background: true` so the server keeps running. Report the URL and the background task id back to the user. The server binds to loopback only — every file in the workspace is readable to processes on the same host while it runs, so do not place secrets there.

---

## User interaction

Evaluation takes real time (subagents in parallel typically 1–3 minutes × number of prompts). Follow these rules:

- **Before starting, state the plan in one sentence**: "target=X / prompts=3 auto-generated / runs=1 / ETA ~90 s".
- **Right after dispatch, say so**: "launched 6 subagents; will pipe results to grader on completion".
- **Always finish by presenting report.md**: bare numbers don't help — include the verdict and the top 3 fix candidates.

Ask via AskUserQuestion (not free text) whenever a decision is required.

---

## Edge cases

- **No SKILL.md at target_skill_path**: hard fail. The user may have handed you the plugin root — glob `skills/*/SKILL.md` and offer the candidates.
- **evals.json exists but assertions are empty**: same as skill-creator — propose from the prompts and confirm.
- **Dynamic layer: pass_rate is 0 on both configurations**: the prompt is likely too hard or too ambiguous. Report says: rework the prompt.
- **with_skill loses to without_skill**: the skill is net-negative. Before suspecting assertion quality, re-read SKILL.md and check whether it uses `MUST` to enforce an incorrect procedure.

---

## Possible extensions (not implemented)

- Score an entire **plugin** at once (`plugin.json` plus the commands/agents/hooks/skills underneath), rather than a single skill.
- Description optimization (run trigger evals as skill-creator's `run_loop.py` does).
- Cross-skill leaderboard.

These have cleaner ownership as separate skills / plugins.

---

## References

- claude-code plugin conventions for SKILL.md / frontmatter / progressive disclosure → the "Writing Style" / "Skill Writing Guide" sections of claude-plugins-official `skill-creator`'s SKILL.md
- A/B benchmark methodology and JSON schema → claude-plugins-official `skill-creator`'s `references/schemas.md`
- Axis details → `references/eval-axes.md`

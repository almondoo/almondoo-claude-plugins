---
name: skill-eval
description: Evaluate any Claude Code skill on two layers — (1) static structural quality derived from claude-code plugin conventions (frontmatter validity, body length, progressive disclosure, description triggerability) and (2) dynamic A/B benchmarking that runs the same prompts in parallel subagents with-skill vs without-skill and compares pass rate, time, and tokens. Use whenever the user wants to evaluate, audit, benchmark, A/B test, score, or measure the quality of a skill, or when they ask "is this skill any good", "does this skill actually help", or "compare with and without this skill".
---

# skill-eval

Evaluate any Claude Code skill on **two layers — static + dynamic** and emit both a human-readable report and a machine-readable JSON.

The evaluation target is a directory that contains a single `SKILL.md`. Either a standalone skill directory or a per-plugin skill directory (`skills/*` under a `.claude-plugin/plugin.json`) is accepted.

---

## Why two layers

- **Static alone** misses the "well-written but useless in practice" skill.
- **Dynamic alone** misclassifies a skill as "good" when the LLM happened to push through on the day — and the result fails to reproduce in someone else's environment. Structural debt (body too long, over-imperative tone, no progressive disclosure) is also invisible to the execution benchmark.
- Producing both lets the judge demand "structurally sound AND measurably with > without" before shipping.

The axis details live in `references/eval-axes.md`. The thesis that "a skill should explain *why* instead of leaning on `MUST` / `NEVER`" aligns with the claude-code-plugin convention (the Anthropic skill-creator "Writing Style" section).

---

## Inputs

Collect the following from the user (skip whatever has already been provided):

1. **target_skill_path** (required) — directory of the skill to evaluate, e.g. `/path/to/plugins/foo/skills/foo/`. `SKILL.md` must live directly under it.
2. **eval prompts** (optional) — test prompts. If absent, auto-generate 3 from the static result and the SKILL.md description, then confirm.
3. **runs_per_configuration** (optional) — number of repetitions per A/B configuration. Default 1. Suggest 3 only when variance is the question.
4. **skip dynamic?** (optional) — if the user wants static only, skip the dynamic layer.

Ask via AskUserQuestion (do not ask through plain text output).

---

## Workflow overview

```
[Step 1] static_check.py scores structure          → static.json
[Step 2] confirm eval prompts (provided or auto-generated)
[Step 3] for each prompt, dispatch with_skill / without_skill subagents
         in parallel within the same turn
[Step 4] grader (agents/grader.md) scores each run against assertions → grading.json
[Step 5] aggregate_benchmark.py emits benchmark.json + benchmark.md
[Step 6] write a unified report.md combining static + dynamic
```

The workspace lives alongside `target_skill_path` as `<skill-name>-eval-workspace/iteration-N/`. The layout mirrors skill-creator's so that the workspace can later be carried into skill-creator for further iteration.

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
| frontmatter.name_matches_dir | `name:` matches the directory name (the official spec treats omission/mismatch as legal, so **warn** only) | warn |
| frontmatter.description_present | description is non-empty | hard fail if missing |
| frontmatter.description_has_trigger | description includes "when to use" cues (verb + context) | warn |
| frontmatter.description_length | The official cap is `description + when_to_use` combined 1,536 chars (skills.md). The 50-char lower bound is a community heuristic | warn if outside |
| body.line_count | body (after frontmatter) ≤ 500 lines | warn over |
| body.must_never_density | density of `MUST` / `NEVER` / `ALWAYS` (excluding code spans). High ≈ "why" is missing | warn |
| body.no_emoji | no emoji in the body (U+1F300–1FAFF). Technical glyphs (→ ✓ ★ etc.) are exempt | warn |
| structure.has_progressive_disclosure | at least one of references/ scripts/ assets/ exists | info (unnecessary when body is short) |
| structure.scripts_referenced_from_body | files under scripts/ are referenced from SKILL.md | warn unreferenced |
| structure.references_referenced_from_body | same for references/ | warn unreferenced |

**hard_fail semantics**: when any axis with severity=`hard_fail` fails, `hard_fail: true` is flagged and the score is capped at 0.4 (the mathematical reflection of a ship-blocker).
**When frontmatter is absent**: only `frontmatter.present` (severity=hard_fail) is added; the rest of the frontmatter axes are skipped.

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

If `hard_fail: true`, do not run the dynamic layer — prompt the user to fix instead.

---

## Step 2: Confirm eval prompts

If `<target>/evals/evals.json` already exists, adopt it. Otherwise:

1. Generate **3** test prompts from the description and body of SKILL.md.
2. Confirm "are these 3 fine for evaluation?" via AskUserQuestion (edit / add / OK).
3. Once confirmed, persist them as `<workspace>/iteration-N/evals.json`.

Prompt-writing guidance (same thesis as the skill-creator "Description Optimization" section):

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

**Important: dispatch every prompt × both configurations in the same turn.** Running the baseline later misaligns conditions (time-of-day, model load) and ruins comparability.

For each prompt, launch two Agents (`subagent_type: general-purpose`) with `run_in_background: true`:

### with-skill subagent

```
Execute this task. You have access to the following skill - read its SKILL.md first
and follow it for the task:

Skill SKILL.md path: <target_skill_path>/SKILL.md

Task: <eval prompt>

Save all outputs (files, final answer) under:
<workspace>/iteration-N/runs/eval-<id>/with_skill/outputs/

When done, write a short summary to outputs/SUMMARY.md describing what you produced.
```

### without-skill subagent

```
Execute this task WITHOUT using any special skill or external reference. Use only
your default tools.

Task: <eval prompt>

Save all outputs under:
<workspace>/iteration-N/runs/eval-<id>/without_skill/outputs/

When done, write a short summary to outputs/SUMMARY.md describing what you produced.
```

The completion notification of the Agent tool (the `<usage>` block in the return) includes `total_tokens` and `duration_ms`. Persist those **immediately** to `<run-dir>/timing.json` — once the completion notification has passed, the values cannot be retrieved later. Write per child agent as soon as its notification arrives.

```json
{ "total_tokens": 84852, "duration_ms": 23332, "total_duration_seconds": 23.3 }
```

Runs with no `timing.json` are treated as `null` by the aggregator and excluded from stats (so they don't masquerade as a zero).

### Dispatch decision criteria

- Verify the target skill is **read-only / safe** by skimming its SKILL.md. Skills that perform external writes (PR creation, email send, etc.) need sandboxing rather than plain subagents — for now, warn the user and offer to skip the dynamic layer.
- A high prompt-by-configuration count (e.g. 3 × 2 × 3 runs = 18) can blow up parallelism. When `runs_per_configuration > 1`, batch in groups of 6.

---

## Step 4: Grading

Once every run has completed, hand each run's outputs and assertions to `agents/grader.md` (this is a **prompt template without frontmatter** — not a Claude Code agent file). Either Read it into a subagent or paste its contents inline.

Example grader input:

```
Read this prompt template: <this-skill-path>/agents/grader.md (absolute path)
Apply it to grade this run:
  Run directory: <workspace>/iteration-N/runs/eval-<id>/with_skill/
  Assertions: <full list from evals.json>
Write grading.json to the run directory.
```

`grading.json` schema (compatible with the skill-creator viewer):

```json
{
  "expectations": [
    {"text": "...", "passed": true,  "evidence": "..."},
    {"text": "...", "passed": false, "evidence": "..."}
  ],
  "summary": {"passed": 1, "failed": 1, "total": 2, "pass_rate": 0.5}
}
```

The field names (`expectations` / `text` / `passed` / `evidence` / `summary`) are read by key in the aggregator and the viewer — do not rename them.

For programmatically verifiable assertions (file existence, regex match, etc.), instruct the grader to "write a small script to verify". Eyeballing is slow and unreliable.

---

## Step 5: Aggregation

Run `scripts/aggregate_benchmark.py`:

```bash
python3 <this-skill-path>/scripts/aggregate_benchmark.py \
  <workspace>/iteration-N \
  --skill-name <target-skill-name> \
  --out <workspace>/iteration-N/benchmark.json
```

The schema of `benchmark.json` is identical to the skill-creator `references/schemas.md` (`runs[]` / `run_summary.with_skill` / `run_summary.without_skill` / `delta`).

Also emit `benchmark.md` as a human-readable table:

```
| eval | with pass | without pass | Δ pass | with sec | without sec | Δ tokens |
| 1    | 1.00      | 0.33         | +0.67  | 42       | 30          | +1700    |
```

---

## Step 6: Unified report

`scripts/render_report.py` scaffolds `report.md` from `static.json` and `benchmark.json`:

```bash
python3 <this-skill-path>/scripts/render_report.py \
  --static <workspace>/iteration-N/static.json \
  --benchmark <workspace>/iteration-N/benchmark.json \
  --out <workspace>/iteration-N/report.md
```

`--benchmark` is optional (omitting it produces a static-only report). After scaffolding, hand-write the verdict and the top fix candidates.

Minimal manual format:

```markdown
# skill-eval report: <skill-name>

## Verdict
<one-liner: one of "Ship-ready" / "Needs work" / "Net negative" / "Inconclusive">

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
1. (up to 3 items, mixing static and dynamic sources)

## Files
- static.json / benchmark.json / runs/eval-*/{with_skill,without_skill}/outputs/
```

Verdict heuristics (use as guidance only; the user makes the final call):

- **Ship-ready**: static score ≥ 0.8 and pass_rate delta ≥ +0.2
- **Needs work**: static score 0.5–0.8 or pass_rate delta in +0.05–+0.2
- **Net negative**: pass_rate delta ≤ 0, or both time and tokens at least 2× larger
- **Inconclusive**: too few runs or high variance (stddev > mean × 0.3)

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
- **with_skill loses to without_skill**: the skill is net-negative. Before suspecting assertion quality, re-read SKILL.md and check whether it `MUST`-enforces the wrong procedure.

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

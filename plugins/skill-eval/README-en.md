# skill-eval

A plugin that **evaluates any Claude Code skill on two layers** — static structural quality plus dynamic with-skill vs. without-skill A/B benchmarking — and ships a sibling viewer skill that renders the resulting workspace into a designed HTML report.

## What it does

1. **Static layer** — score the skill's structure against claude-code plugin conventions.
   - frontmatter validity (`name` matches directory basename, `description` carries when-to-use cues, length within the official 1,536-char cap and a community 50-char floor)
   - SKILL.md body length (≤ 500 lines as a guideline)
   - progressive disclosure (`references/` / `scripts/` / `assets/` / `agents/` / `prompts/`)
   - imperative tone, density of `MUST` / `NEVER` / `ALWAYS` markers (each one expected to be justified)

2. **Dynamic layer** — run **with-skill vs. without-skill subagent A/B**, modeled after `skill-creator`'s approach.
   - the same eval prompts dispatched in parallel under both configurations within a single turn
   - assertion-based grading (pass rate)
   - time (seconds) and token consumption delta
   - aggregated into `benchmark.json` + `benchmark.md`

3. **Proposal derivation** — `report.md`'s "Top issues to fix" is hand-written from four sources (static FAIL / differentiating assertions / time-token-variance anomalies / dogfooding gap), prioritized by an outcome-changing counterfactual. See `skills/skill-eval/references/proposal-derivation.md`.

4. **HTML rendering** — the sibling `skill-eval-viewer` skill renders the workspace (`report.md` + `static.json` + `benchmark.json` + `NN-*.md` sub-reports) into a single self-contained HTML file. Optional `--serve` mode binds a local HTTP server on `127.0.0.1`.

## Glossary

Terms used throughout the report and the docs. The HTML report omits these definitions intentionally — first-time readers should land here.

- **Static layer** — mechanical structural scoring of SKILL.md (frontmatter, body length, progressive disclosure).
- **Dynamic layer** — runs real prompts with and without the skill in parallel, scoring outputs against the same assertion list.
- **A/B benchmark** — running the same prompt under two conditions (with_skill / without_skill) at the same time to compare effects. The dynamic layer's underlying method.
- **with_skill / without_skill** — two subagent conditions. One reads the target's SKILL.md before acting (with_skill); the other uses only its default behavior (without_skill).
- **hard_fail** — a static-layer condition signalling a ship-blocking structural defect (e.g., no frontmatter). Caps the score at 0.4 and skips the dynamic layer.
- **pass_rate delta** — difference between with_skill and without_skill assertion pass rates. Crossing +0.2 is one of the Ship-ready conditions.
- **Differentiating assertion** — an assertion that passes only under one configuration (typically with_skill). Makes the skill's contract visible.
- **runs_per_configuration** — number of repetitions per A/B condition. Use ≥3 to measure variance.
- **iteration** — one complete skill-eval pass. All artefacts land under `iteration-N/` in the workspace.
- **verdict** — the call: `Ship-ready` / `Needs work` / `Net negative` / `Inconclusive`. Ship-ready needs static ≥ 0.8 AND pass_rate delta ≥ +0.2. Net negative is delta < 0, or time ≥ 2× AND tokens ≥ 2×. Inconclusive is an additive flag for high-variance runs.

## When it triggers

Activated via Claude's automatic skill-triggering when the user asks things like "evaluate this skill", "benchmark with vs. without this skill", "audit this skill against claude-code plugin conventions", or "is this skill any good". No slash command is provided.

The viewer skill triggers on requests to render a skill-eval workspace as HTML or share an evaluation report visually.

## Requirements

- Python 3.10+ (scripts run on the standard library; `parse_frontmatter` opportunistically uses PyYAML when available)

## Directory layout

```
plugins/skill-eval/
├── .claude-plugin/plugin.json
├── README.md
└── skills/
    ├── skill-eval/                   # the evaluator
    │   ├── SKILL.md
    │   ├── scripts/
    │   │   ├── static_check.py       # structural scoring
    │   │   ├── aggregate_benchmark.py # with / without aggregation
    │   │   └── render_report.py      # static.json + benchmark.json → report.md scaffold
    │   ├── references/
    │   │   ├── eval-axes.md          # axis-by-axis rationale
    │   │   ├── step-3-dispatch.md    # full subagent dispatch shapes
    │   │   ├── step-4-grading.md     # grader contract and grading.json schema
    │   │   ├── step-5-aggregation.md # benchmark.json schema and missing-data semantics
    │   │   └── proposal-derivation.md # "Top issues to fix" derivation guide
    │   ├── agents/
    │   │   └── grader.md             # plain prompt template for the grader subagent (not a dispatchable agent file)
    │   └── evals/
    │       └── evals.json            # this skill's own test cases
    └── skill-eval-viewer/            # the HTML renderer
        ├── SKILL.md
        ├── references/frontend-design.md
        └── scripts/
            └── render_html.py        # workspace → report.html (file or --serve mode)
```

Development history and design decisions live outside the plugin, at the repo root in `docs/learnings/skill-eval.md` (not shipped when the plugin is installed).

## Output artifacts (per iteration)

```
<workspace>/iteration-N/
├── evals.json                    # source of truth for this iteration's prompts and assertions
├── static.json                   # static-layer scoring
├── benchmark.json                # dynamic-layer aggregate (skill-creator-compatible schema)
├── benchmark.md                  # human-readable summary table
├── report.md                     # final human-facing report (verdict + Top fix + files)
├── report.html                   # optional, produced by skill-eval-viewer
└── runs/eval-N/
    ├── with_skill/    { outputs/, grading.json, timing.json }
    └── without_skill/ { outputs/, grading.json, timing.json }
```

## See also

- `skills/skill-eval/SKILL.md` — the full skill spec (Inputs, six-step workflow, verdict heuristics, proposal-derivation pointer)
- `skills/skill-eval-viewer/SKILL.md` — the viewer's contract (workspace inputs, file vs. serve delivery modes, design notes)
- `docs/learnings/skill-eval.md` at the repo root — design decisions, iteration history, and known follow-ups (lives outside the plugin so it is not distributed with the install)

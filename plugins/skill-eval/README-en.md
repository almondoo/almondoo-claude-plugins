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
├── docs/
│   └── LEARNINGS.md                  # iteration history, design decisions, gotchas
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
        └── scripts/
            └── render_html.py        # workspace → report.html (file or --serve mode)
```

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

- `docs/LEARNINGS.md` — design decisions, iteration history, and known follow-ups (kept in Japanese as an internal operations log)
- `skills/skill-eval/SKILL.md` — the full skill spec (Inputs, six-step workflow, verdict heuristics, proposal-derivation pointer)
- `skills/skill-eval-viewer/SKILL.md` — the viewer's contract (workspace inputs, file vs. serve delivery modes, design notes)

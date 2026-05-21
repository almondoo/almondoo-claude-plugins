# skill-eval

A plugin that **evaluates any Claude Code skill across two layers**.

## What it does

1. **Static layer** — scores the skill's structure against claude-code plugin conventions.
   - Frontmatter validity (`name` matches the directory name / `description` includes "when to trigger" cues / length is in range)
   - SKILL.md body length (~500 lines as a guideline)
   - Progressive disclosure (use of `references/` / `scripts/` / `assets/`)
   - Imperative tone / no overuse of `MUST` / `NEVER`

2. **Dynamic layer** — runs **with-skill vs without-skill subagent A/B execution**, the same approach used by skill-creator.
   - Same test prompts executed in parallel under both configurations
   - Assertion grading (pass rate)
   - Time (seconds) / token consumption delta
   - Aggregated into benchmark.json + benchmark.md

## When it triggers

When the user says things like "evaluate this skill" / "benchmark with vs without" / "score this skill's quality" (via Claude's skill auto-trigger). No slash command is provided.

## Prerequisites

- Python 3.10+ (scripts use only the stdlib; PyYAML is used by `parse_frontmatter` when available)

## Directory layout

```
plugins/skill-eval/
├── .claude-plugin/plugin.json
├── README.md
└── skills/
    └── skill-eval/
        ├── SKILL.md
        ├── scripts/
        │   ├── static_check.py         # structural scoring
        │   ├── aggregate_benchmark.py  # aggregates with/without results
        │   └── render_report.py        # static.json + benchmark.json → report.md
        ├── references/
        │   └── eval-axes.md            # evaluation axis details
        ├── agents/
        │   └── grader.md               # assertion grading prompt template (not a Claude Code agent)
        └── evals/
            └── evals.json              # test cases for this skill itself
```

## Output example

```
report.md          ... human-readable report
static.json        ... static scoring result
benchmark.json     ... with/without aggregation (skill-creator-compatible schema)
runs/eval-N/
  with_skill/outputs/...
  without_skill/outputs/...
```

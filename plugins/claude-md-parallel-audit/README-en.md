# claude-md-parallel-audit

**Multi-agent parallel audit** of CLAUDE.md (and sibling agent-instruction files such as `CLAUDE.local.md` / `AGENTS.md` / `GEMINI.md`), surfacing **HIGH-severity** quality issues. Detection targets include missing qualifiers, grammar errors, term inconsistency, logical contradictions across sections, implicit assumptions, missing enumerations, and undefined terms.

## What runs, in what order

The skill iterates until convergence or `max_iterations` (default `5`):

1. **Phase 1**: collect target file path / `N` / `threshold` / `max_iterations` / exclusion list via `AskUserQuestion` (defaults: `N=9`, `threshold=4`, `max_iterations=5`).
2. **Phase 1.5**: draft a one-line purpose for each section, then batch-confirm (the intent baseline used by `fix-safety-checker`).
3. **Phase 2**: dispatch N parallel `auditor` agents with `model: "sonnet"` in a single turn (up to 10 HIGH-severity findings per instance).
4. **Phase 3**: produce two tables — per-instance HIGH count, and convergent issues (≥ threshold).
5. **Phase 4 / 4.5 / 4.6**: triage → `false-positive-detector` (REAL / FALSE / NEEDS_HUMAN) → `default-redundancy-checker` (does it duplicate the Claude Code default? KEEP / SIMPLIFY / REMOVE).
6. **Phase 5 / 5.5 / 5.6**: fix draft (single / multi-option) → `fix-safety-checker` (SAFE / NEEDS_REVIEW / UNSAFE) → per-fix approval via `AskUserQuestion`.
7. **Phase 6**: apply with `Edit` (if the auto-mode classifier rejects an agent-config file, obtain explicit authorization and retry once).
8. **Phase 7 / 8**: re-dispatch from Phase 2 → check convergence (all N clean / at least `(N − threshold + 1)` clean / HIGH-count plateau / max_iter reached / zero fix candidates).

## Install

```
/plugin marketplace add almondoo/almondoo-claude-plugins
/plugin install claude-md-parallel-audit@almondoo-claude-plugins
```

## Usage

```
/claude-md-parallel-audit:claude-md-parallel-audit
```

The skill activates automatically when the user requests **audit / review / verification / quality check** of CLAUDE.md or similar instruction files, mentions keywords such as *multi-agent audit* / *convergence audit* / *parallel review* / *instruction file consistency*, or asks for highly reliable, reproducible detection of defects in long instruction files.

## Layout

```
claude-md-parallel-audit/
├── .claude-plugin/
│   └── plugin.json
├── skills/
│   └── claude-md-parallel-audit/
│       ├── SKILL.md                       # main skill definition
│       ├── agents/                        # specialized subagents
│       │   ├── auditor.md
│       │   ├── default-redundancy-checker.md
│       │   ├── false-positive-detector.md
│       │   └── fix-safety-checker.md
│       └── evals/
│           └── evals.json                 # trigger / behavior tests
└── README.md
```

## Difference from template-comparison audits

This skill is built around **independent parallel auditing + reproducibility threshold** and does not perform template matching. It is **complementary** to template-comparison audits such as the official marketplace's `claude-md-management:claude-md-improver`, not a replacement.

## License

[Apache-2.0](../../LICENSE)

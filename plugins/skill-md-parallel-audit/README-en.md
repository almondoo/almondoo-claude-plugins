# skill-md-parallel-audit

**Multi-agent parallel audit** of SKILL.md (Claude Code plugin skill specification files), surfacing **HIGH-severity** quality issues. Detection targets include missing qualifiers, grammar errors, term inconsistency, logical contradictions across sections, implicit assumptions, missing enumerations, and undefined terms. This is the **sibling** of `claude-md-parallel-audit`: the shared engine (`auditor` / `false-positive-detector` / `fix-safety-checker`) is extended with SKILL.md-specific exclusion defaults and a redundancy check against other skills.

## What runs, in what order

The skill iterates until convergence or `max_iterations` (default `5`):

1. **Phase 1**: collect target SKILL.md path / `N` / `threshold` / `max_iterations` / exclusion list via `AskUserQuestion` (defaults: `N=9`, `threshold=4`, `max_iterations=5`; exclusions include SKILL.md-specific default candidates — Claude Code official `subagent_type` types, the `<this-skill-path>` placeholder convention, cross-skill references).
2. **Phase 1.5**: draft a one-line purpose for each section, then batch-confirm (the intent baseline used by `fix-safety-checker`).
3. **Phase 2**: dispatch N parallel `auditor` agents with `model: "sonnet"` in a single turn (up to 10 HIGH-severity findings per instance).
4. **Phase 3**: produce two tables — per-instance HIGH count, and convergent issues (≥ threshold).
5. **Phase 4 / 4.5 / 4.6**: triage → `false-positive-detector` (REAL / FALSE / NEEDS_HUMAN) → `skill-md-redundancy-checker` (does it overlap with other skills — skill-creator / skill-eval / etc.? KEEP / SIMPLIFY / REMOVE).
6. **Phase 5 / 5.5 / 5.6**: fix draft (single / multi-option) → `fix-safety-checker` (SAFE / NEEDS_REVIEW / UNSAFE) → per-fix approval via `AskUserQuestion`.
7. **Phase 6**: apply with `Edit`.
8. **Phase 7 / 8**: re-dispatch from Phase 2 → check convergence (all N clean / at least `(N − threshold + 1)` clean / HIGH-count plateau / max_iter reached / zero fix candidates).

## Install

```
/plugin marketplace add almondoo/almondoo-claude-plugins
/plugin install skill-md-parallel-audit@almondoo-claude-plugins
```

## Usage

```
/skill-md-parallel-audit:skill-md-parallel-audit
```

The skill activates automatically when the user requests things like "audit this SKILL.md", "stamp out ambiguity in the skill spec", or "review skill quality with multiple agents".

## Layout

```
skill-md-parallel-audit/
├── .claude-plugin/
│   └── plugin.json
├── skills/
│   └── skill-md-parallel-audit/
│       ├── SKILL.md                            # main skill definition
│       ├── agents/                             # specialized subagents
│       │   ├── auditor.md                      # shared engine (copy)
│       │   ├── false-positive-detector.md      # shared engine (copy)
│       │   ├── fix-safety-checker.md           # shared engine (copy)
│       │   └── skill-md-redundancy-checker.md  # SKILL.md-specific
│       └── evals/
│           └── evals.json                      # trigger / behavior tests
└── README.md
```

## Difference from claude-md-parallel-audit

| Aspect | claude-md-parallel-audit | skill-md-parallel-audit |
|---|---|---|
| Target files | CLAUDE.md / AGENTS.md family | SKILL.md |
| Phase 1 exclusion defaults | (none) | Claude Code official `subagent_type` types / `<this-skill-path>` placeholder convention / cross-skill references |
| Phase 4.6 redundancy | Against the Claude Code default system prompt | Against other skills (skill-creator / skill-eval / etc.) |
| Shared engine (`auditor.md` / `false-positive-detector.md` / `fix-safety-checker.md`) | Identical | Identical (copy) |

## Related plugins

- `claude-md-parallel-audit` — sibling for CLAUDE.md-family files
- `skill-eval` — structural scoring + dynamic A/B (orthogonal to the prose audit that this plugin provides)

## License

[Apache-2.0](../../LICENSE)

# parallel-audit

**Multi-agent parallel audit** of agent-instruction markdown files (CLAUDE.md / CLAUDE.local.md / AGENTS.md / GEMINI.md / SKILL.md), surfacing **HIGH-severity** quality issues. Detection targets include missing qualifiers, grammar errors, term inconsistency, logical contradictions across sections, implicit assumptions, missing enumerations, and undefined terms.

## Positioning

**Designed as a diagnostic tool for specific symptoms, not as routine maintenance.** Intended triggers:

- Verification right after a large refactor / many added rules
- Noticing that a specific rule is being ignored or misapplied
- Observed agent-behavior drift
- Behavior changes after a Claude model upgrade — isolating whether CLAUDE.md is the cause

Routine use is explicitly not recommended (cost mismatch + remaining findings reach an asymptote). Phase 1 emits a warning and asks for explicit confirmation when the user selects "routine".

## What runs, in what order

Iterates until convergence or `max_iterations` (default `3`):

1. **Phase 1**: symptom interview (`AskUserQuestion`) → warn + confirm if "routine" is selected
2. **Phase 1.5**: scope narrowing (full file / section / rule-and-neighbors) — restrict audit surface
3. **Phase 2**: collect target_file / `N` / `threshold` / `max_iterations` / exclusion list (defaults `N=3` / `threshold=2` / `max_iterations=3`). `target_type` (claude-md | skill-md) is auto-detected from path
4. **Phase 2.5**: when target is SKILL.md and `skill-eval` is available, run its static pre-check
5. **Phase 3**: draft a one-line purpose per section, then batch-confirm (the intent baseline used by `fix-safety-checker`)
6. **Phase 4**: dispatch N parallel `auditor` agents with `model: "sonnet"` in a single turn
7. **Phase 5**: produce two tables — per-instance HIGH count, and convergent issues (≥ threshold)
8. **Phase 6 / 7**: triage → `false-positive-detector` (REAL / FALSE / NEEDS_HUMAN) → `redundancy-checker` (target_type-branched: Claude Code defaults or sibling skills, KEEP / SIMPLIFY / REMOVE)
9. **Phase 8 / 9 / 10**: fix draft (single / multi-option) → `fix-safety-checker` (SAFE / NEEDS_REVIEW / UNSAFE) → per-fix approval via `AskUserQuestion`
10. **Phase 11**: apply with `Edit` (if an agent config such as CLAUDE.md / CLAUDE.local.md / ~/.claude/skills/* is rejected by the auto-mode classifier, obtain explicit authorization and retry once)
11. **Phase 11.5**: post-fix verification — (a) re-dispatch audit / (b) optional A/B benchmark (`references/ab-testing.md`) / (c) re-run `skill-eval` static check when target is SKILL.md
12. **Phase 12**: convergence check (all N clean / at least `(N − threshold + 1)` clean / HIGH-count plateau / `max_iterations` / zero fix candidates)

## Install

```
/plugin marketplace add almondoo/almondoo-claude-plugins
/plugin install parallel-audit@almondoo-claude-plugins
```

## Usage

```
/parallel-audit:parallel-audit
```

The skill is **intended to activate automatically** when the user requests **audit / review / verification / quality check** of an instruction file (CLAUDE.md / SKILL.md and similar), mentions keywords such as *multi-agent audit* / *convergence audit* / *parallel review* / *instruction file consistency* / *audit my SKILL.md*, or asks for highly reliable, reproducible detection of defects in long instruction files. See "Known limitations" below for the current triggering caveat.

## Known limitations

- **In-session triggering recall is unmeasured.** The only triggering measurement runs through skill-creator's `claude -p` backend, where the skill recorded recall = 0% on 4 should-trigger evals. In-session triggering is a different code path, but has not been re-measured. Until that's done, **invoke the skill explicitly** (`/parallel-audit:parallel-audit` or naming the skill in your prompt) when you want it.
- **Should-trigger evals are trace-reviewed, not end-to-end benchmarked.** Phase 1 / 2 / 3 / 10 / 11 `AskUserQuestion` calls block subagent runs, so eval ids 1–4 are verified by trace review (reading SKILL.md prose) rather than end-to-end execution. Only the should-not-trigger evals (5–7) have end-to-end benchmarks.
- **Phase 9 fan-out cost can exceed the headline range.** For defect-rich files (5+ fix candidates × multi-option mode), Phase 9 alone can dispatch 10–15 safety-checkers and push verification overhead 4–9× above the cost-tier table's "+20–80k" estimate. See SKILL.md "Known limitations" for the worst-case math.
- **External-target operating sample size = 1** (`~/.claude/CLAUDE.md`). Behaviors specific to less-common CLAUDE.md / SKILL.md shapes remain unobserved.

## Layout

```
parallel-audit/
├── .claude-plugin/
│   └── plugin.json
├── skills/
│   └── parallel-audit/
│       ├── SKILL.md                       # main skill definition
│       ├── agents/
│       │   ├── auditor.md                 # 7-axis HIGH-severity audit (file-type agnostic)
│       │   ├── false-positive-detector.md
│       │   ├── fix-safety-checker.md
│       │   └── redundancy-checker.md      # branches on target_type (defaults vs siblings)
│       ├── references/
│       │   ├── claude-md-specifics.md          # CLAUDE.md exclusion defaults + auto-mode classifier playbook
│       │   ├── skill-md-specifics.md           # SKILL.md exclusion defaults + skill-eval integration
│       │   ├── shared-blind-spots.md           # target-type-agnostic shared FP patterns (referenced from both specifics)
│       │   ├── ab-testing.md                   # Phase 11.5(b) optional A/B integration guide
│       │   ├── pitfalls.md                     # workflow / aggregation / fix-proposal / target-specific pitfalls
│       │   └── symptom-interview-protocol.md   # Phase 1 symptom structuring protocol
│       └── evals/
│           └── evals.json                 # trigger / behavior tests
└── README.md
```

## Relationship to the previous two plugins

This skill is the unified successor to `claude-md-parallel-audit` (v0.2.1) and `skill-md-parallel-audit` (v0.2.1). Both plugins will be removed from the marketplace after a few releases. Existing users should migrate to `parallel-audit`.

Key changes:

- Two plugins merged (`target_type: claude-md | skill-md` branches the behavior)
- Default `N` reduced from `9` → `3` (event-driven positioning; deep audit is opt-in)
- New Phase 1 symptom triage + scope narrowing (narrow the audit surface before full-file dispatch)
- Phase 11.5 post-fix verify standardized (audit re-dispatch + optional A/B)
- `max_iterations` default `5` → `3` (reflects the observed asymptote)

## Difference from template-comparison audits

This skill is built around **independent parallel auditing + reproducibility threshold** and does not perform template matching. It is **complementary** to template-comparison audits such as the official marketplace's `claude-md-management:claude-md-improver`, not a replacement.

## License

[Apache-2.0](../../LICENSE)

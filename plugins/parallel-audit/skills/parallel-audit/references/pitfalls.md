# pitfalls

Pitfalls observed across parallel-audit invocations. Read at Phase 1 if you're new to the skill, or when a phase isn't behaving as expected. The orchestrator should not need to consult this in steady-state — each phase's own instructions in SKILL.md are authoritative.

## Workflow & phase ordering

- **Skipping Phase 1 symptom interview** → routine audits run by default. Always run Phase 1 even if the user "seems to know what they want"; the symptom shapes scope and A/B decision.
- **Forgetting the exclusion list** → subagents re-flag intentional design every iteration; convergence never reaches. Always collect exclusions in Phase 2 with `references/<target>-specifics.md` pre-loaded defaults.
- **Skipping Phase 3 section purposes** → `fix-safety-checker.intent_preserved` becomes circular (judged by re-reading the section being changed).
- **Running routine without symptom** → Phase 1 emits a warning; honor it. Routine use of this skill is anti-pattern — the asymptote means the same findings recur and waste tokens.
- **Skipping Phase 11.5(a) re-verify** → "I applied 2 fixes, done" is premature. Without re-verification, you don't know if fixes actually changed convergence behavior.
- **Skipping Phase 6.5 / 7 / 9 verification subagents** → ≥threshold convergence does not guarantee correctness. The 3 phases catch shared-misreading false positives, redundant rules, and unsafe fixes.

## Aggregation & dispatch

- **Modifying the audit prompt to "improve" it** → breaks reproducibility. The 7 axes and exclusion section are load-bearing; touch only the placeholders.
- **Dispatching subagents serially** → wastes time. Always dispatch all N in one message with `run_in_background: true`.
- **Treating "below threshold" issues as fixable** → ≥ threshold is the bar. Below that, signal is too noisy to trust.
- **Main-thread aggregation drift** → quietly downgrading subagent findings during Phase 5 defeats the purpose of multi-agent audit. Subagents read in fresh contexts; you read with accumulated session bias.
- **Letting Phase 9 verdict be overridden silently** → if `fix-safety-checker` returns UNSAFE, do not present that fix to the user unmodified.
- **Refining a redundant rule instead of removing it** → honor Phase 7's REMOVE / SIMPLIFY classification.

## Fix proposal & apply

- **Batching all fix proposals into one question** → user rubber-stamps or rejects everything. One AskUserQuestion per fix.
- **Using single-proposal mode for substantive fixes** → forcing the user into "Apply / Skip / Modify (free text)" wastes their time. Use multi-option mode when the fix is substantive.
- **Retrying auto-mode-blocked Edits blindly** → without explicit AskUserQuestion authorization, the classifier blocks every retry. Follow the `references/claude-md-specifics.md` playbook.
- **Ignoring `rule_burden_impact: INCREASES_MAJOR`** → adding rules has real cost. Surface major increases in the AskUserQuestion description, do not bury.
- **Applying overlapping fixes in approval order** → two fixes touching the same line span (or within ±2 lines) cause the second Edit to fail (or worse, land in the wrong location). Apply per the Phase 11 line-range conflict pre-check: group transitively by overlap, sort groups bottom-up by max line number, apply within-group bottom-up, re-Read + re-verify `before` text between fixes in a group, re-dispatch `fix-safety-checker` on any stale `before`, never use an "Apply-as-is" bypass.
- **Applying non-overlapping fixes without re-Read between groups** → INSERT/REMOVE-class fixes in one group shift line numbers for downstream groups; the bottom-up group ordering converts this from "shifts upstream" (corrupting) to "shifts already-applied" (no-op), but only if you ordered groups correctly. If you skip the between-group re-Read, downstream fixes get stale line numbers.

## Phase 2 input validation

- **Silently coercing invalid `N` / `threshold` / `max_iterations` to defaults** → user expects validation to surface their mistake, not invisible correction. Re-ask up to 3 times with the violated constraint stated; after the 3rd failed attempt, present an AskUserQuestion offering defaults / abort / one-more-attempt — never silently coerce. Constraints: `2 ≤ N ≤ 9`, `2 ≤ threshold ≤ N − 1`, `2 ≤ max_iterations ≤ 10`. `threshold == N` is rejected because `(N − threshold + 1) = 1` makes a single clean instance vacuously satisfy practical convergence; `max_iterations = 1` is rejected because Phase 11.5(a)'s `iteration < max_iterations` gate would never fire.

## Target-specific

- **Treating cross-skill references as automatic defects (SKILL.md target)** → if the SKILL.md inlines the load-bearing content AND points to the canonical source as a courtesy, that is not a defect.

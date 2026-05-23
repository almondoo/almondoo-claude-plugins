# symptom-interview-protocol

## Role

Reference for **Phase 1** of the parallel-audit skill. The main thread reads this file and follows the protocol to structure the user's reason for invoking the skill into a `symptom` value that shapes Phases 1.5 / 2 / 11.5. This is a protocol document — there is no subagent involved (the file lives in `references/` for that reason).

## Why this matters

The parallel-audit skill is positioned as an **event-driven diagnostic**, not routine maintenance. The defaults (`N=3`, `threshold=2`, `max_iterations=3`) are calibrated for diagnostic use. Running the skill on "I just want to check my CLAUDE.md" with no specific symptom wastes tokens on noise the user already saw last time (the 7-axis taxonomy reaches an asymptote; same convergent findings recur).

Phase 1 therefore asks the user to name the symptom before the audit starts. The answer determines:

- **Phase 1.5 scope choice** (full file vs. section vs. rule-and-neighbors)
- **Phase 2 `ab_testing_enabled` recommendation** (drift symptom → suggest A/B)
- **Phase 11.5(c) emphasis** (pre-shipping SKILL.md → ensure static re-check)

For "routine" answers, Phase 1 emits a warning and requires explicit confirmation — this is the one place where the skill actively discourages its own use.

## Protocol

### Step 1: Ask the user via AskUserQuestion

Present these six options exactly as listed. Phrase the question as: "Why are you auditing this file? (This shapes audit scope and post-fix verification.)"

| Option | Label | Description shown to user |
|---|---|---|
| post-refactor | Post-refactor verification | I just added or restructured multiple rules and want to verify nothing broke |
| specific-rule | A specific rule is being ignored / misapplied | I noticed agent behavior conflicts with a specific rule; want to find what's wrong around that rule |
| drift | General agent behavior drift | Agent behavior has changed; not sure if the instruction file is the cause |
| pre-shipping | Pre-shipping check (SKILL.md before publishing) | About to ship this SKILL.md; want a structural + prose final pass |
| post-model-upgrade | Post-model-upgrade isolation | Behavior changed after a Claude model upgrade; isolating whether the instruction file is the cause |
| routine | Routine maintenance check | No specific symptom — periodic checkup |

### Step 2: Branch on the answer

#### post-refactor

- Pass `scope_hint: full-file` to Phase 1.5 (refactor effects cross sections; need full view)
- Pass `ab_testing_recommended: false` to Phase 2 (user wants verification, not measurement)
- No additional setup

#### specific-rule

- Ask a follow-up AskUserQuestion: "Which rule? Provide the section heading or paste the rule text"
- Pass `scope_hint: rule-and-neighbors`, `scope_target: <section or rule text>` to Phase 1.5
- Pass `ab_testing_recommended: false` to Phase 2 (focused fix doesn't need A/B)

#### drift

- Pass `scope_hint: full-file` to Phase 1.5 (cause unknown; need full view)
- Pass `ab_testing_recommended: true` to Phase 2 (drift is measurable; A/B can isolate whether file edits help)
- Explicitly tell the user: "If you have a benchmark task set, A/B verification will give a measurable signal. Otherwise consider whether the symptom may be model/hooks/prompt rather than the instruction file"

#### pre-shipping

- Only valid for `target_type == "skill-md"`. If `target_type == "claude-md"`, redirect: "Pre-shipping check is for SKILL.md targets. For CLAUDE.md you may want 'post-refactor verification' instead."
- Pass `scope_hint: full-file` to Phase 1.5
- Set `ensure_phase_2_5: true` so Phase 2.5 static check is treated as required (not optional)
- Set `ensure_phase_11_5c: true` so Phase 11.5(c) static re-check feeds the Phase 12 ship-ready criterion

#### post-model-upgrade

- Pass `scope_hint: full-file` to Phase 1.5
- Pass `ab_testing_recommended: false` to Phase 2 (model itself changed; A/B before/after the file edits won't isolate the model effect)
- Note to user: "Audit will find wording that's ambiguous enough to parse differently across models. Fixing those defects narrows the search; if behavior still differs after audit-clean, the model itself is the cause"

#### routine

This is the discouraged case. Emit this warning and require explicit confirmation:

> This skill is designed as an event-driven diagnostic, not routine maintenance.
>
> For routine use:
> - The 7-axis taxonomy reaches an asymptote — the same findings recur and waste tokens
> - Expected cost: ~150k tokens per iteration × 3 iterations = ~450k tokens per run
> - For routine instruction-file health, lighter alternatives exist: a single-pass Claude review (~30k tokens), or `claude-md-improver` for template-based gap analysis (~50k tokens)
>
> Are you sure you want to proceed with parallel-audit?

Use AskUserQuestion with options:

- "No, I'll use a lighter tool instead" — abort gracefully, suggest one of the lighter alternatives
- "Yes, I have a specific concern but no clear symptom — proceed anyway" — set `scope_hint: full-file`, `ab_testing_recommended: false`, log the override
- "Yes, proceed (one-time exploratory run)" — same as above

If the user aborts, end the skill invocation politely. Do not run the audit.

### Step 3: Return the structured symptom

After branching, pass the following to the rest of the workflow:

```
symptom: <one of: post-refactor | specific-rule | drift | pre-shipping | post-model-upgrade | routine>
scope_hint: <one of: full-file | section | rule-and-neighbors>
scope_target: <optional, set for specific-rule>
ab_testing_recommended: <true | false>
ensure_phase_2_5: <optional, true for pre-shipping>
ensure_phase_11_5c: <optional, true for pre-shipping>
routine_override: <optional, true if user proceeded after the routine warning>
```

Phase 1.5 reads `scope_hint` and `scope_target` to set the audit scope. Phase 2 reads `ab_testing_recommended` to seed the A/B default. Phase 2.5 / 11.5(c) check the `ensure_*` flags. Phase 12 reads `routine_override` and includes it in the final report (so the user sees their override decision in context).

## Constraints

- **Always run Phase 1.** Do not skip even when the user's initial message seems to specify intent — explicit symptom selection structures the rest of the workflow consistently.
- **Do not infer the symptom from the user's wording.** Ask. Wording can be ambiguous ("review my CLAUDE.md" could be post-refactor, drift, or routine).
- **Honor the routine warning.** If the user says "routine" → emit warning → user picks "lighter tool", abort. Do not proceed with the audit just because the symptom interview ran.
- **Do not edit `agents/auditor.md` based on the symptom.** The audit prompt is byte-identical across all dispatches; symptom only affects scope (Phase 1.5) and verification layers (Phase 11.5).

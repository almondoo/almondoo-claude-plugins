# ab-testing

Optional integration with `skill-eval`'s with/without benchmark for Phase 11.5(b). Loaded only when `ab_testing_enabled: true` is set in Phase 2 AND `skill-eval` is installed as an external dependency.

## External dependency requirement

`skill-eval` is NOT bundled in this marketplace (`almondoo-claude-plugins`). For A/B testing to function, the user must have installed `skill-eval` separately (from a different marketplace, from source, or via the same resolution chain documented in `references/skill-md-specifics.md` under "Resolving `<skill-eval-path>`").

If `ab_testing_enabled: true` is set but `skill-eval` cannot be resolved, Phase 11.5(b) is **skipped with a prominent warning** ("Phase 11.5(b) skipped — `ab_testing_enabled: true` was opted in but `skill-eval` is not available at any resolved path. Install skill-eval and re-run to get A/B verification, or accept this audit without it."). The audit itself completes normally — A/B is purely supplemental verification, not gating.

## When to enable

A/B testing produces a measurable signal that fixes actually changed downstream agent behavior. Without it, the audit's only success signal is "auditors stop flagging the same things" — a closed loop that proves nothing about real-world agent quality.

Enable A/B testing when:

- The Phase 1 symptom is **drift** (behavior has changed and you want to verify whether instruction-file fixes restored it)
- The Phase 1 symptom is **specific-rule** AND you have a benchmark task that exercises the rule (you can measure whether the fix changed task success on that specific task)
- You are running a high-stakes refactor on a CLAUDE.md / SKILL.md that drives many sessions and you want quantitative justification for the fixes

Do NOT enable A/B testing when:

- The Phase 1 symptom is **routine** (no specific symptom → A/B can only measure noise)
- The Phase 1 symptom is **post-model-upgrade** (the model changed; A/B before/after instruction-file edits won't isolate the model effect)
- You don't have a benchmark task set (this skill does NOT curate one for you; see "User-supplied requirement" below)
- The audit budget is tight (A/B multiplies per-iteration cost; the multiplier ranges from ~1.7× at the smallest configuration up to ~9× at the largest — see the cost table below to size against your specific task / trial counts)

## Why default OFF

Two reasons:

1. **Signal-to-noise is fundamentally hard.** Most CLAUDE.md / SKILL.md fixes are wording-level changes whose effect on a single benchmark task is small and noisy. You typically need many trials × many tasks to detect a 5-10% success-rate differential. Without that, the A/B result is noise dressed up as measurement.
2. **No automatic task curation.** The skill cannot synthesize a benchmark task set for you. Running A/B on a poorly chosen task set produces a misleading "verified" stamp on fixes that didn't actually matter — worse than no A/B at all.

If neither of those concerns applies to your case, opt in at Phase 2.

## How it works (Phase 11.5(b) integration)

After Phase 11 applies the iteration's fixes:

1. **Snapshot the pre-fix file** — `git stash` or copy the file to a temp path before the fixes were applied. If the user is on a feature branch, the previous commit's version is the pre-fix snapshot.
2. **Run skill-eval's benchmark twice** — once with the pre-fix file in place, once with the post-fix file in place. The benchmark task set comes from the user (see "User-supplied requirement" below).
3. **Aggregate per-task results** — pass rate, mean tokens, mean duration. Show the delta (post − pre) per task.
4. **Report the verdict**:
   - Delta ≥ +10 percentage points on the targeted tasks → strong positive signal
   - Delta within ±5 pp → no signal (likely noise; the fixes may not have mattered for these tasks)
   - Delta ≤ −10 pp → negative signal; the fixes regressed behavior. Roll back or re-audit
   - Mixed: some tasks +X, others −X → surface per-task results so the user can decide which fixes to keep

The skill does NOT automatically roll back on negative signal. The user decides — Phase 11.5(b)'s job is to give them the data.

## User-supplied requirement

A/B testing requires a benchmark task set with at least:

- **3-5 representative tasks** that should exercise the rules in the audited section(s). One task per rule, when possible.
- **Per-task acceptance criteria** that skill-eval can check programmatically (assertion functions). Subjective "looks good" tasks are not usable for A/B because the differential signal is too noisy.
- **Reasonable execution time per task** — A/B doubles the run, so a task that takes 30s in baseline becomes ~1 minute in A/B. Long-running tasks (>5 min) are expensive at scale.

If the user does not have such a task set, the skill's recommendation is one of:

1. **Skip A/B for this audit** — set `ab_testing_enabled: false` and proceed without it. The fix decisions rely on the user's judgment via Phase 10 AskUserQuestion approvals.
2. **Curate a task set first** — use `skill-creator`'s eval workflow to draft 3-5 tasks tailored to the symptom, then re-invoke parallel-audit with `ab_testing_enabled: true`.
3. **Use a single canonical task** — if the user has a single representative task they care about, run that 5-10 times in baseline and post-fix to estimate the differential. Less statistically robust than a task set but still better than no measurement.

The Phase 2 question for `ab_testing_enabled` should make these three fallbacks visible so the user can pick the right one for their situation.

## Cost estimate

| A/B mode | Per-iteration cost (approx) | Notes |
|---|---|---|
| Disabled (default) | 1× audit cost (e.g., 150k at N=3) | Phase 11.5(b) skipped |
| Enabled, 3 tasks × 5 trials each | 1× audit + ~250k benchmark | Per-trial cost depends on task; this estimate assumes ~25k per trial |
| Enabled, 5 tasks × 10 trials each | 1× audit + ~1.2M benchmark | Approaches the cost of a full deep audit by itself |

Surface this cost at Phase 2 so the user can size their task set appropriately. A common pattern: enable A/B only on the final iteration (when the audit has converged) rather than on every iteration.

## Interpretation guidance

Honest about what A/B can and cannot say:

- **Can say**: "fixing these specific defects in this specific section changed task success on this specific benchmark by X percentage points"
- **Cannot say**: "the audit found defects that mattered to real-world agent behavior in general" (the benchmark is a proxy, not the population)
- **Cannot say**: "the asymptote findings don't matter" (the benchmark may not exercise them)

A small or no-effect A/B result does not invalidate the audit; it means the chosen benchmark didn't measure the effect. Either find a better benchmark or accept that the fixes are improvements on the dimensions the audit measures (prose clarity) rather than on the dimensions A/B measures (specific task behavior).

## Constraints

- **Never enable A/B silently.** Always go through the Phase 2 question — running A/B without explicit user opt-in is a cost surprise.
- **Always snapshot the pre-fix file.** Without a baseline, the post-fix run has nothing to compare against.
- **Do not interpret a positive A/B result as universal validation.** It validates the fixes against the specific benchmark. State this scope explicitly in the report.
- **Do not roll back automatically on a negative A/B.** Surface the result; the user decides.

---
name: iterative-refine
description: Use when running iterative refinement loops (implement → verify → fix → re-verify) inside the current conversation - establishes explicit exit conditions (success, max iterations, oscillation, escape attempts) and forbids in-loop verification cheating (test skips, assertion weakening, broad ignore comments). Prevents premature termination at "good enough", scope drift to unrelated files, and silent goalpost shifts. Not for cross-session loops - use /loop (ScheduleWakeup-based) for that.
---

# iterative-refine

Inline iterative refinement loop with explicit termination structure. Use this skill when a task requires repeated "implement → verify → fix" cycles within a single conversation and you need a framework that prevents the common failure modes of open-ended self-refinement.

## When to use

- "Make all tests pass"
- "Fix every type / lint error"
- "Refactor X until `<objective check>` passes"
- Anything where the loop is bounded by an objective check, not by subjective judgment

## When NOT to use

- One-off tasks with no iteration (single edit, single command)
- Tasks whose exit criterion can only be judged subjectively (e.g., "make it look better")
- Cross-session work where the loop must survive across conversation boundaries — use `/loop` (ScheduleWakeup-based) instead

## Required inputs

If any of these are missing, ask the user via `AskUserQuestion` **before** starting the loop:

1. **Goal** — one concrete sentence (e.g., "all `pnpm test` cases pass on the current branch")
2. **Verification command** — a deterministic shell command whose exit code defines success (e.g., `pnpm test && pnpm tsc --noEmit && pnpm lint`)
3. **Max iterations** — integer (default: 5)
4. **Scope** — files/globs that may be edited and those that must not. If unspecified, default to "files touched in the current diff plus their tests"

## The loop

For each iteration `N = 1..MAX`:

1. Run the verification command, capturing stdout and stderr
2. If exit code == 0 → **success**: report and stop
3. Parse failures into a list and create one `TaskCreate` per failure
4. Apply minimal fixes (one `TaskUpdate completed` per failure resolved)
5. Compare the current verification output to the previous iteration's output. If byte-equal (after trimming trailing whitespace), increment `oscillation_count`; otherwise reset to 0
6. If `oscillation_count >= 2` → **oscillation**: stop and report
7. If `N == MAX` → **max-iterations**: stop and report

## Termination conditions (priority order)

| Code | Trigger | Required action |
|---|---|---|
| `success` | Verification exits 0 | Report final verification output (last ~20 lines) |
| `escape-attempt` | About to skip/disable a test, weaken an assertion, edit snapshots instead of producers, or modify the verification command | Stop immediately, surface via `AskUserQuestion` |
| `oscillation` | Same verification output two iterations in a row, no progress | Stop, report what was tried, ask the user for direction |
| `max-iterations` | `N` reached `MAX` without success | Stop, report best state and remaining failures |

`escape-attempt` takes precedence over `oscillation` and `max-iterations`: never run "one more iteration" if doing so would require an escape.

## Forbidden in-loop behaviors

The following are **escape attempts**. Trigger `escape-attempt` immediately if any becomes tempting:

- Modifying the verification command itself (the goalpost cannot move mid-loop)
- Adding `.skip` / `xfail` / `@pytest.mark.skip` / `it.skip` / `it.todo` / commenting out a failing test
- Weakening assertions or expected values to make them pass
- Editing snapshot / expected-output files instead of fixing the producer
- "Fixing" unrelated files that happen to be in the current diff (scope creep)
- Suppressing lint or type errors with broad ignores (`// @ts-ignore`, `# type: ignore`, `eslint-disable`, `noqa`) without explicit user permission for that specific line

If any of these become tempting, that is a signal to **stop and report**, not a signal to push harder.

## Output structure

When stopping for any reason, report in this exact shape so the user can quickly diagnose:

```
Reason: <success | oscillation | max-iterations | escape-attempt>
Iterations: N / MAX
Final verification (exit <code>):
  <last ~20 lines of output>
Changes made:
  <git diff --stat or equivalent>
Unresolved (if applicable):
  - <failure 1>
  - <failure 2>
Next-step suggestion: <one sentence>
```

## Example

User says:

> "`pnpm test && pnpm tsc --noEmit` が全部 pass するまで直して。最大 5 反復で。`src/auth/` 以下だけ触っていい。"

Translate to inputs:

- **Goal**: `pnpm test && pnpm tsc --noEmit` exits 0
- **Verification**: `pnpm test && pnpm tsc --noEmit`
- **Max iterations**: 5
- **Scope (allowed)**: `src/auth/**` and the test files covering those modules
- **Scope (forbidden)**: everything else, the verification command itself, any test skip

Then run the loop per the section above.

## Relationship to other skills

- `superpowers:test-driven-development` — embeds a similar loop inside red → green → refactor. Prefer TDD when the task is explicitly test-first; use `iterative-refine` for non-TDD iterative work
- `superpowers:verification-before-completion` — mandates a single verification before claiming complete. `iterative-refine` extends that single check into a multi-iteration loop with explicit termination
- `superpowers:systematic-debugging` — hypothesis → test → refine, scoped to bug-hunting. Prefer it when the task is "find the bug"; use `iterative-refine` when the task is "make the verification pass"
- `/loop` (top-level skill) — cross-session loop via `ScheduleWakeup`. Use when the loop must survive across conversation boundaries (e.g., wait 30 min for CI); `iterative-refine` is exclusively for within-session loops

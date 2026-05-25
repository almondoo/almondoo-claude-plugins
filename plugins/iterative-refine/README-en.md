# iterative-refine

A framework skill for running "implement → verify → fix → re-verify" loops within a single session. Explicit termination conditions (success / max iterations / oscillation / verification-escape attempts) prevent premature stopping, scope drift, and verification cheating (test skips, assertion weakening, verification-command rewrites).

## Why

Asking Claude to "iterate until convergence" works, but without objective criteria the loop tends to:

- Stop at "good enough" (premature termination)
- When stuck, silently skip/delete tests and report "passing" (verification cheating)
- Oscillate between two states without progress (oscillation)
- "Fix" unrelated files along the way (scope drift)

These failure modes stem from leaving discretion to the agent. This skill removes that discretion with an explicit framework: termination conditions, forbidden actions, and a fixed output format.

## When to use

- "Fix everything until all tests pass"
- "Resolve every type / lint error"
- "Iterate until `<verification command>` exits 0"

Use `/loop` (ScheduleWakeup-based) only when the loop must survive across sessions (e.g., waiting 30 minutes for CI). For inline self-refinement, `iterative-refine` is the right tool.

## Required inputs

The skill asks via `AskUserQuestion` for anything missing at start time:

1. **Goal** — one sentence (e.g., "all `pnpm test` cases pass")
2. **Verification command** — a shell command whose exit code defines success
3. **Max iterations** — default 5
4. **Scope** — files/globs allowed and forbidden

## Termination conditions

| Code | Trigger |
|---|---|
| `success` | Verification command exits 0 |
| `escape-attempt` | About to skip a test, weaken an assertion, rewrite the verification command, overwrite a snapshot, or apply a broad ignore |
| `oscillation` | Same verification output two iterations in a row (no progress) |
| `max-iterations` | Limit reached without success |

`escape-attempt` takes top priority: never "do one more iteration" if it requires weakening the verification.

## Install

```
/plugin install iterative-refine@almondoo-claude-plugins
```

See [SKILL.md](skills/iterative-refine/SKILL.md) for the full skill. Japanese version: [README.md](README.md).

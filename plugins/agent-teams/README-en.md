# agent-teams

A team-composition skill for implementing multiple tasks in parallel, organized into **Waves**. It spawns Lead + Implementer + Reviewer + Tester (and an optional dedicated Security Checker for large or security-critical work) in a single Phase 2 batch, with code review, security checks, and a final full regression wired in as **quality gates**.

## Why this exists

Lining up implementer agents alone drops quality — review, security checks, and test verification fall through the cracks. Worse, if multiple teammates run `git add` / `git commit` concurrently in the same working tree, one teammate's untracked / staged files get swept into another teammate's commit (real incident).

This skill prevents both problems by construction:

- **Quality gates**: one task = one commit, review per commit, exactly one Tester full regression at the end of each wave.
- **Lead-exclusive git**: destructive git is the Lead's alone, and even the Lead may only run `git add` (per-path) and `git commit` (no `--amend`). Every other destructive operation (`reset` / `restore` / `push` / `rebase` / `merge` / `revert` / `--amend` / `branch -D` / `clean` / `stash drop` / `worktree remove`, …) is **forbidden even for the Lead**.

## Team composition

Size the team by task scale:

| Scale | Headcount | Composition |
|-------|-----------|-------------|
| Small (1-2 files) | 2 | Lead + Implementer×1 + Reviewer×1 (security and tests combined) |
| Medium (3-5 files) | 3-4 | Lead + Implementer×1-2 + Reviewer×1 (security combined) + Tester×1 |
| Large (6+ files) or security-critical | 5-6 | Lead + Implementer×2-3 + Reviewer×1 + Security Checker×1 (dedicated) + Tester×1 |

**Security upgrade**: any task involving auth / authorization, payments, PII or sensitive data, newly exposed API endpoints, or file uploads bumps up by one scale tier (a 2-file change becomes Medium when it implements JWT auth).

## Wave structure

The typical pattern is **"4 in parallel + 2 blocked_by"**, six tasks total.

```
Wave A (4 tasks in parallel): impl-A / impl-B / impl-C / impl-D
Wave B (blocked_by Wave A): 2 tasks
```

Naming convention: `W<n>-<D|A|AI|UI><id>` (D=doc, A=api, AI=ai, UI=ui).

## File ownership

**1 file = 1 owner.** Tasks are split along file boundaries; no two teammates ever edit the same file concurrently. Shared-file changes are either consolidated under one teammate or serialized across Waves.

## Workflow

1. **Phase 1 (planning)**: the Lead reads the issue / spec / git log, picks 6 tasks, decides the Wave structure, and gets user approval.
2. **Phase 2 (single-batch spawn)**: `TeamCreate` → `TaskCreate` → spawn Implementer + Reviewer + Tester (+ Security Checker) **in one message**. Reviewer / Tester wait idle until a SendMessage activates them.
3. **Phase 3 (execution)**: Implementer implements + verifies locally → requests a commit from the Lead → Lead runs `git add <path>` + `git commit` on their behalf → Reviewer reviews → on Critical / Important, Lead sends a fix request to the Implementer. **The fix cycle is capped at 3 iterations**; on non-convergence the Lead halts and escalates to the user.
4. **Phase 4 (disband)**: after all Reviewer PASS, the Tester runs the final regression exactly once → `shutdown_request` to everyone → `TeamDelete`.

## Why the Tester runs only once at end-of-wave

In a past Wave, per-commit Tester requests caused the Tester to become unresponsive in the latter half due to context pressure. Since Implementer self-verification + Reviewer PASS already establish per-commit quality, **the Tester is called only once at end-of-wave**, focused on post-accumulation consistency.

## Templates included

| File | Purpose |
|------|---------|
| `assets/spawn-prompts/implementer.md` | Implementer spawn-prompt template |
| `assets/spawn-prompts/reviewer.md` | Reviewer spawn-prompt template (OWASP Top 10 perspectives baked in) |
| `assets/spawn-prompts/security-checker.md` | Dedicated Security Checker spawn-prompt template |
| `assets/spawn-prompts/tester.md` | Tester spawn-prompt template (lightweight output format) |
| `assets/wave-template.md` | Wave composition patterns (naming convention / owner separation / completion conditions) |
| `assets/lead-checklist.md` | Lead's per-phase checklist |
| `references/git-permissions.md` | Full git-operations table with Lead allow/deny + Implementer workflow |
| `references/implementer-pitfalls.md` | Frequent traps (literal control bytes, off-target edits, etc.) |
| `references/tester-optimization.md` | Tester request consolidation + Lead direct-verification fallback |

## Prerequisites

This skill depends on the Claude Code **Agent Teams** runtime (the deferred tools `TeamCreate` / `TaskCreate` / `TaskUpdate` / `TaskList` / `TaskGet` / `SendMessage` / `TeamDelete`). Confirm before invoking:

- Claude Code **CLI** (the VSCode extension has historically disabled the task-management tools — prefer the CLI for this skill).
- A recent CLI version with the Agent Teams feature available.
- Depending on your environment, the Agent Teams capability may be gated behind an experimental flag (e.g. `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`); check the official docs for the version you are running.

If the Step 0 `ToolSearch` does not return all seven schemas, the Lead reports the failure via `AskUserQuestion` and refuses to substitute `Agent` — the substitution would structurally collapse Lead-exclusive git and every quality gate.

## Install

```
/plugin marketplace add almondoo/almondoo-claude-plugins
/plugin install agent-teams@almondoo-claude-plugins
```

## Usage

Automatic triggering is **disabled** (`disable-model-invocation: true`); the skill is invoked explicitly:

```
/agent-teams work through issue 123
/agent-teams implement auth feature
/agent-teams add several helpers in parallel
```

If the argument is ambiguous, the Lead asks via `AskUserQuestion` before entering Phase 1 — silent spawn from a guessed interpretation is forbidden.

### Step 0: mandatory `ToolSearch`

The team-management tools this skill relies on — `TeamCreate` / `TaskCreate` / `SendMessage` / `TaskUpdate` / `TeamDelete` and friends — are **deferred tools**, so their schemas are not loaded at session start. The skill's first action must be a single `ToolSearch` call to load them all. Skipping this step silently routes parallelism through the `Agent` tool, which breaks Lead-exclusive git, the per-commit review gate, and every other core invariant.

## License

Apache-2.0

---
name: agent-teams
description: Implement multiple tasks in parallel with quality gates via agent teams. Use for digesting an entire issue, building large features in waves, or adding multiple helpers in one shot. Spawns Implementer + Reviewer + Tester team, with the Lead holding exclusive control over `git add` / `git commit` to prevent race conditions while progressing wave by wave.
disable-model-invocation: true
argument-hint: Task description (e.g. "work through issue 123" / "implement auth feature" / "add several helpers in parallel")
---

# Agent Teams: Best Practice Team Composition

Agent Teams are powerful, but lining up implementer agents alone drops quality. Code review, security checks, and test verification fall through the cracks. This skill guarantees a team composition appropriate to the task size, and structurally embeds rules learned from past incidents (Lead's centralized git control, Tester request consolidation, control-byte defense).

## When this skill is invoked

The user invokes this explicitly via `/agent-teams <task description>` (automatic triggering is disabled). The argument is the user's request (e.g. `work through issue 123` / `implement auth feature` / `add multiple helpers in parallel`).

### Step 0 (mandatory before anything else): Load team-management tools

The tools this skill needs — `TeamCreate` / `TaskCreate` / `SendMessage` / `TaskUpdate` / `TaskList` / `TaskGet` / `TeamDelete` — are all **deferred tools**. Their schemas are not loaded by default at session start, and calling them directly will fail with `InputValidationError`.

As the very first action when the skill starts, run `ToolSearch` exactly once, before any planning or AskUserQuestion:

```
ToolSearch({
  query: "select:TeamCreate,TaskCreate,SendMessage,TaskUpdate,TeamDelete,TaskList,TaskGet",
  max_results: 7
})
```

**Why this matters**: the `Agent` tool is always loaded directly and has zero call-time friction, while the team-management tools above are deferred. This asymmetry creates a silent-fallback pressure: if you start planning before loading these tools, the path of least resistance is to dispatch parallel work via `Agent` instead, which **breaks every core invariant of this skill** (Lead-exclusive git, 1 task = 1 commit, contamination detection, Tester consolidation, Phase 2 simultaneous spawn). Loading once upfront removes that pressure.

If `ToolSearch` returns an error for any of these tool names, stop and report to the user via `AskUserQuestion` — do not proceed by substituting `Agent`. The substitution is not an alternative execution path; it is a failure mode.

### Lead's first actions (first 3-5 minutes)

1. **Parse the argument and grasp the user's intent**
   - If there is an issue number, fetch it with `gh issue view <N>`
   - Check for overlap with existing commits via `git log --grep` etc.
   - If anything is unclear, ask via AskUserQuestion (e.g. "Which area should we start from?")

   **Argument interpretation guide** — apply this table to decide what to confirm:

   | Argument shape | Default interpretation | Must-confirm? |
   |---|---|---|
   | `work through issue <N>` | Fetch the issue with `gh issue view <N>`, turn its AC into tasks | Confirm only if AC is ambiguous after fetch |
   | `implement <feature name>` | Grep for matching spec / design doc and start there | **Must confirm** if no doc is found |
   | `add several helpers` / `add multiple X` | "Which helpers / which X" is the load-bearing info | **Must confirm** — never guess |
   | `refactor <module>` | Read current code, present a refactor direction in Plan mode | Confirm the direction in the Plan step |
   | `fix bug in <area>` | Reproduction steps + expected behavior are required | **Must confirm** |
   | Anything else not matching above | Treat as ambiguous | **Must confirm** |

   When in doubt, AskUserQuestion. Silent spawn from a guessed interpretation is forbidden.

2. **Enter Plan mode and draft an implementation plan** (see Workflow Phase 1 below)
3. **Decide the team composition** (see "Deciding the team composition" below)
4. **Decide the Wave structure** (typical: 4 in parallel + 2 blocked_by; details in `assets/wave-template.md`)
5. **Present the plan to the user → get approval → proceed to Phase 2 spawn**

Do not silently execute `TeamCreate` / `TaskCreate` / spawn without approval — these are large operations, so confirming user intent is mandatory.

## Required Roles

Every task needs the following roles. Whether they are dedicated or combined depends on scale, but no role may be omitted.

| Role | Primary responsibilities |
|------|--------------------------|
| **Team Lead** (you) | Task splitting, progress tracking, integration, final decisions, **exclusive execution of `git add` (per-path) and `git commit` (no amend)** |
| **Implementer** (≥1) | Feature implementation, unit test authoring, local verification (vitest / typecheck / lint) → request commits from the Lead |
| **Reviewer** | Code review, spec compliance, security review (when combined) |
| **Tester** | One final full regression run at the end of a wave |
| **Security Checker** | Dedicated security review (may be combined with Reviewer depending on conditions) |

### Lead responsibilities summary

| Phase | What the Lead does |
|---|---|
| Phase 1 (plan) | Pick 6 tasks from the backlog → decide Wave structure (e.g. 4 in parallel + 2 blocked_by) → get user approval |
| Phase 2 (spawn) | TeamCreate / TaskCreate / spawn 6 teammates at once (Implementer + Reviewer + Tester) |
| Phase 3 (execute) | Take Implementer commit requests and run `git add <path>` + `git commit -m "..."` on their behalf / dispatch reviews / steer the fix cycle |
| Phase 4 (disband) | Request a final regression from the Tester → send shutdown_request to everyone → TeamDelete → report a summary to the user |

For details, see `assets/lead-checklist.md`.

## Deciding the team composition

### Step 1: Judge the scale

Consider not just file count but also **security importance**.

```
Baseline:
  Small:  1-2 file changes
  Medium: 3-5 files, multiple modules
  Large:  6+ files, architectural changes

Security upgrade: if the task matches any of the following, step up by one tier
  - Authentication / authorization (JWT, OAuth, session management)
  - Payment / billing
  - Handling of PII or sensitive data
  - Newly exposed API endpoints
  - File uploads / external input handling

Example: even a 2-file change becomes "medium" composition when it implements JWT auth.
```

### Step 2: Decide the composition

| Scale | # of teammates | Composition |
|---|---|---|
| Small | 2 | Lead + Implementer×1 + Reviewer×1 (review + security + tests all combined) |
| Medium | 3-4 | Lead + Implementer×1-2 + Reviewer×1 (security combined) + Tester×1 |
| Large or security-critical | 5-6 | Lead + Implementer×2-3 + Reviewer×1 + Security Checker×1 (dedicated) + Tester×1 |

### When to make Security Checker a dedicated role

Only when one of the following applies, add a dedicated **Security Checker** alongside the Reviewer:

- Large task (6+ files)
- Task matches a security upgrade (auth / payment / PII / etc.)

Otherwise the Reviewer covers security as a secondary role. Even in the "Reviewer + security combined" case, always include OWASP Top 10 perspectives in the spawn prompt (see `assets/spawn-prompts/reviewer.md`).

## File ownership principle

**1 file = 1 owner. Never let multiple teammates edit the same file concurrently.**

If two teammates edit the same file in parallel, one's changes overwrite the other's. Resolving merge conflicts produces rework and waste. At the task-splitting stage, assign edit rights for each file exclusively to one teammate.

### Rules when splitting tasks

1. **Split owners along file boundaries**: align task boundaries with file boundaries. When splitting "implement feature A", assign file X to Implementer A and file Y to Implementer B.
2. **Consolidate shared-file changes into one person**: if multiple tasks need to change the same file (e.g. index.ts, config, shared type definitions), consolidate edits to that file under a single teammate, or serialize them across Waves (`blocked_by`) so they never run concurrently.
3. **State assigned files explicitly in the spawn prompt**: list the files each teammate may edit, and state explicitly that all other files are off-limits.

## Lead's git permissions (canonical definition)

**Among destructive git operations, the only ones the Lead may execute are `git add` (per-path) and `git commit` (no amend)**. All other destructive operations (`reset` / `restore` / `checkout <file>` / `push` / `rebase` / `merge` / `revert` / `cherry-pick` / `commit --amend` / `branch -D` / `clean` / `stash drop|clear` / `worktree remove` etc.) are forbidden even for the Lead.

**Non-destructive git operations (`status` / `log` / `diff` / `show` / `blame` / `reflog` / `fetch` / `stash push|pop|list|apply` / `branch <new>` / `tag <new>` / `worktree add` etc.) may be executed freely by every teammate.**

Implementers must not execute any destructive git operations. They only implement and verify locally, then request commits from the Lead via SendMessage → the Lead performs them on their behalf.

**For details (full operations table / rationale / how to handle contamination / Implementer workflow), see `references/git-permissions.md`.**

## Workflow

### Phase 1: Planning

1. Understand the user's request and grasp the overall scope
2. Read the issue / spec / git log, then pick 6 target tasks from the backlog
   - Prefer new helpers / high independence / no Prisma migration / no new dependencies
   - Verify they don't overlap with existing commits (search for similar task names with `git log --grep`)
3. **Decide the Wave structure** — typical is "4 in parallel + 2 blocked_by" (details: `assets/wave-template.md`):
   - Naming convention `W<n>-<D|A|AI|UI><id>` (D=doc / A=api / AI=ai / UI=ui)
   - Owner separation by file (1 file = 1 owner)
4. Present the plan (team composition + Wave structure + 6-task outline) to the user and get approval

### Phase 2: Create the team and spawn everyone at once

1. **TeamCreate** to make the team
2. Split tasks and register with **TaskCreate**
   - Set `blocked_by` to express dependencies (Wave structure)
   - Aim for ~5-6 tasks per teammate
3. Remind the user to enable **Delegate mode (Shift+Tab)** (so the Lead doesn't hijack implementation)
4. **Spawn every role's teammate at once in Phase 2** (Implementer + Reviewer + Tester, plus Security Checker if needed)
   - State explicitly in the spawn prompt that Reviewer / Tester "wait until SendMessage instructs you"
   - "Spawn the Reviewer after implementation finishes" is forbidden: spawning on demand loses context and degrades review quality

Build spawn prompts by **copying the templates in `assets/spawn-prompts/` and replacing placeholders**. Per-file:
- `assets/spawn-prompts/implementer.md`
- `assets/spawn-prompts/reviewer.md`
- `assets/spawn-prompts/tester.md`
- `assets/spawn-prompts/security-checker.md`

Each template **must include** (already baked into the templates):
- A clear role definition
- A listing of assigned files / directories (exclusive, with forbidden areas also listed)
- Project context (tech stack, architecture, CLAUDE.md constraints)
- Acceptance criteria (what counts as done)
- Workflow (Implementer: local verify → request commit from Lead / Reviewer & Tester: wait for SendMessage)
- **Explicit git write permissions** (all destructive forbidden / non-destructive free) — details: `references/git-permissions.md`
- **literal control-byte caveat** (Implementer only, details: `references/implementer-pitfalls.md`)

### Phase 3: Execution and quality gates (continuous SendMessage interaction)

The Lead acts purely as an **orchestrator**. Never use the Edit tool on code (implementation belongs to Implementers). Only `git add` + `git commit` git operations are executed by the Lead on behalf of Implementers. When fixes are needed, always send a SendMessage to the Implementer.

#### Per-task cycle

```
1. Implementer self-claims a task and starts working
2. Implementer finishes implementation + local verification → SendMessage to Lead to request a commit
   (Request contents: file paths, counts (vitest pass + typecheck/lint green), acceptance criteria, control-byte check `[]`, proposed commit message)
3. Lead checks scope with `git status` → runs `git add <per-path>` → `git commit -m "..."` on their behalf
4. Lead → SendMessage to Implementer: "commit <hash> done" → Implementer marks TaskUpdate completed
5. Lead → SendMessage to Reviewer: "Please review commit <hash>, files: ..."
6. Reviewer reviews → reports back to Lead via SendMessage
7. If there are Critical / Important findings:
   a. Lead → SendMessage to Implementer: "Please fix the following: ..."
   b. Implementer fixes → local verification → requests fix commit from Lead
   c. Lead runs the fix commit on their behalf (`fix(scope): #issue reviewer C-N ...`)
   d. Lead → SendMessage to Reviewer: "Please verify the fix"
   e. Reviewer re-checks → repeat until OK
8. Tester is NOT called in this cycle (Implementer self-verification + Reviewer quality gate already establish commit-level quality)
9. Task N done → Implementer moves on to the next task
```

**The Tester is called exactly once at the end of the wave** (full regression). See `references/tester-optimization.md`.

#### Fix-cycle guardrails

The Reviewer ↔ Implementer fix loop in step 7 can spiral if the same class of Critical / Important keeps recurring. To stop runaway loops:

- **Cap per task: `MAX_FIX_ITERATIONS = 3`** (each iteration = one Implementer fix + Reviewer re-check)
- Lead tracks the iteration count per task locally (a small note table is enough; do **not** write it into the TaskCreate description because teammates also write there and race conditions clobber notes)
- If iteration 3 still produces Critical / Important on the same task:
  1. Lead halts the cycle and instructs the Reviewer to summarize the remaining findings
  2. Lead also asks the Implementer for a brief diagnosis of why the fixes haven't converged
  3. Lead escalates to the user via AskUserQuestion with these options:
     - `(1) Defer this task to a follow-up issue and continue the wave with what passes`
     - `(2) Reassign the task to a different Implementer (fresh context)`
     - `(3) Pause for new direction from the user`
- Until the user decides, the rest of the wave continues — do not block other Implementers on a single stuck task.

Iteration 1 → 2 fix cycles are expected and healthy. Convergence by iteration 3 is the bar; beyond that the task is signalling a design problem that needs a human, not more code.

#### Optimizing parallel work

When there are multiple Implementers, or when one can pick up the next task while waiting on a review:

```
Implementer A: task 1 implementation done → review pending → starts task 3
Implementer B: implementing task 2
Reviewer: reviewing task 1

* But never run tasks that touch the same file in parallel.
```

#### Wave completion → disband

```
1. Lead confirms all tasks are completed and all Reviewer PASS
2. Lead → SendMessage to Tester to request the final full regression (once only)
3. On Tester PASS, send shutdown_request to all teammates → TeamDelete
4. Report a wave summary to the user
```

If the Tester takes longer than 3× its expected time (about 6 min for a typical ~1-2 min run) without responding, the Lead may run verification commands directly via Bash (Lead direct-verification route, details: `references/tester-optimization.md`). This is read-only objective verification and does not bypass the quality gate.

For a detailed checklist, see `assets/lead-checklist.md`.

## Things you must not do

### Skill-active `Agent`-tool prohibition (overrides the global parallelism rule)

- **Use the `Agent` tool to dispatch parallel implementation / review / test / security work while this skill is active**: all parallelism in this skill MUST go through `TeamCreate` + `TaskCreate` + teammate dispatch (and SendMessage interaction). The global "Parallel Execution for Speed" directive — "2+ independent subtasks → parallel `Agent` calls" — is **explicitly overridden for the duration of this skill**. The agent-teams flow IS the parallelism mechanism here; routing around it via `Agent` defeats every quality gate (Reviewer, Tester, Security Checker) and the Lead's exclusive git control, and structurally re-introduces the race conditions this skill was built to eliminate.
  - Allowed exception (Phase 1 only): the Lead may use `Agent` with `subagent_type: Explore` for **read-only** investigation (issue lookup, code exploration, doc search) to shorten Phase 1 planning. This is read-only and bypasses no quality gate. From **Phase 2 onward (TeamCreate done), all `Agent` invocations are forbidden** without exception — implementation, review, test, and security work must be done by teammates spawned through the team mechanism, not by `Agent` subagents.
- **"Fall back to `Agent` because TeamCreate / TaskCreate / SendMessage failed"**: do not. A failed call means Step 0 was skipped or the tool name is wrong. Re-run `ToolSearch` and fix the call; never silently substitute `Agent`.

### Composition / spawn
- **Build a team of only Implementers**: implementation without review has no quality guarantee
- **Skip reviews**: do not "batch up reviews for later" — review per task
- **Have Implementers review their own code**: a different teammate is required
- **Spawn Reviewer / Tester later**: spawn all teammates at once in Phase 2 and interact via SendMessage. Spawning on demand loses context and degrades quality

### File ownership
- **Let multiple teammates edit the same file**: the single biggest source of overwrite accidents

### Lead-related
- **Hijack implementation**: use Delegate mode and stay focused on coordination
- **Use Edit / Write to fix code yourself**: no matter how small the fix, send a SendMessage to the Implementer. If the Lead touches code, the Reviewer / Tester quality gates are bypassed
- **Run destructive git operations other than `add` / `commit`**: `git reset` / `--amend` / `git restore` / `git push` / `git rebase` / `git merge` / `git revert` / `stash drop|clear` / `branch -D` / `clean` etc. are forbidden even for the Lead. Trying to "clean things up" with a destructive operation causes history-destruction incidents. When such an operation is genuinely needed, ask the user to run it manually via AskUserQuestion
- **Bundle multiple tasks into one commit**: strict "1 task = 1 commit". A commit that mixes tasks ends up with a commit message that can only mention one of them, and splitting it later requires destructive operations
- **Do "leftover work" after disbanding the team**: every piece of work must be completed by a teammate. The Lead doing "the final polish" collapses the quality gate
  - Exception: when the Tester becomes unresponsive, the Lead may run read-only verification commands (e.g. `bun run test:unit`) on its behalf — this does not count as bypassing the quality gate (see `references/tester-optimization.md`)

### Implementer-related
- **Let Implementers run destructive git operations**: destructive operations including `git add` / `git commit` are forbidden on the Implementer side; the Lead runs them. If Implementers commit concurrently, race conditions pull in other teammates' untracked / staged files. Non-destructive ones (status / log / diff / fetch / stash push|pop etc.) are free for Implementers too
- **Let Implementers run destructive operations to "clean up" commits**: trying to "fix contamination" with `git reset` / `--amend` / `git restore` in a shared workspace can roll back other teammates' commits. When an Implementer notices contamination, they **must consult the Lead via SendMessage**, and the Lead decides whether to ask the Implementer for a new fix commit or to follow-up the issue separately
- **Let Implementers embed literal control bytes in source**: even when an Implementer intends `'\x00'` in a NULL-byte rejection test, the tool may expand it into a literal 0x00 byte. Always verify with python3 before committing (see `references/implementer-pitfalls.md`)

### Tester-related
- **Request per-commit verification from the Tester**: Implementer self-verification + Reviewer PASS already establish per-commit quality. Per-commit requests squeeze the Tester's context and cause it to go unresponsive in the latter half of the wave. **The Tester must only be requested for the final full regression at the end of the wave**, once (`references/tester-optimization.md`)
- **Demand verbose output from the Tester**: tables + line-number-annotated analysis + per-metric verdicts are unnecessary. For PASS, 3-5 lines suffice (counts + verdict + no off-target contamination); for FAIL, include blocker details. Specify this in the spawn prompt

## References

For details, consult the following reference files:

| File | Contents | When to consult |
|---|---|---|
| `assets/spawn-prompts/implementer.md` | Implementer spawn-prompt template | During Phase 2 spawn |
| `assets/spawn-prompts/reviewer.md` | Reviewer spawn-prompt template | During Phase 2 spawn |
| `assets/spawn-prompts/tester.md` | Tester spawn-prompt template | During Phase 2 spawn |
| `assets/spawn-prompts/security-checker.md` | Security Checker spawn-prompt template | During Phase 2 spawn (when dedicated) |
| `assets/wave-template.md` | Wave composition patterns (naming convention / owner separation / completion conditions) | During Phase 1 planning |
| `assets/lead-checklist.md` | Lead checklist (checkpoints per phase) | At each phase transition |
| `references/git-permissions.md` | Full git operations table + Implementer workflow details | When uncertain about git decisions |
| `references/implementer-pitfalls.md` | control bytes / other frequent pitfalls | When writing spawn prompts / educating Implementers |
| `references/tester-optimization.md` | Tester request consolidation + Lead direct-verification route + expected-time table | When making Tester-related decisions |

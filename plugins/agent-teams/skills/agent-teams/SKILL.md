---
name: agent-teams
description: Orchestrate a multi-role agent team (Lead + Implementer + Reviewer + Tester, plus optional dedicated Security Checker) to deliver multiple tasks in Waves with built-in quality gates. Use for digesting an entire issue, building large features in waves, or adding multiple helpers in one shot. The Lead holds exclusive control over `git add` / `git commit` to prevent shared-workspace race conditions while progressing wave by wave.
disable-model-invocation: true
argument-hint: [task description | issue number]
---

## Prerequisites

This skill depends on the Claude Code **Agent Teams** runtime (the deferred tools `TeamCreate` / `TaskCreate` / `TaskUpdate` / `TaskList` / `TaskGet` / `SendMessage` / `TeamDelete`). Confirm before invoking:

- Claude Code CLI (the VSCode extension has historically disabled the `Task*` family — prefer the CLI for this skill).
- Recent CLI version with the Agent Teams feature available.
- If your environment requires it, the Agent Teams capability may be gated behind an experimental flag (e.g. `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`); verify against the version of Claude Code you are running.

If `ToolSearch` in Step 0 (below) does not return all seven schemas, stop and report to the user via `AskUserQuestion` — do not silently substitute `Agent`.

# Agent Teams: Best Practice Team Composition

Agent Teams are powerful, but lining up implementer agents alone drops quality. Code review, security checks, and test verification fall through the cracks. This skill guarantees a team composition appropriate to the task size, and structurally embeds rules learned from past incidents (Lead's centralized git control, Tester request consolidation, control-byte defense).

## When this skill is invoked

The user invokes this explicitly via `/agent-teams <task description>` (automatic triggering is disabled). The argument is the user's request (e.g. `work through issue 123` / `implement auth feature` / `add multiple helpers in parallel`).

### Step 0 (mandatory before anything else): Load team-management tools

The tools this skill needs — `TeamCreate` / `TaskCreate` / `SendMessage` / `TaskUpdate` / `TaskList` / `TaskGet` / `TeamDelete` — are all **deferred tools**. Their schemas are not loaded by default at session start, and calling them directly will fail with `InputValidationError`.

As the very first action when the skill starts, run `ToolSearch` exactly once, before any planning or AskUserQuestion:

```
ToolSearch({
  query: "select:TeamCreate,TaskCreate,SendMessage,TaskUpdate,TeamDelete,TaskList,TaskGet"
})
```

(`select:<name1>,<name2>,...` is an exact-name fetch; `max_results` is unused in this mode.)

**Why this matters**: the `Agent` tool is always loaded directly and has zero call-time friction, while the team-management tools above are deferred. This asymmetry creates a silent-fallback pressure: if you start planning before loading these tools, the path of least resistance is to dispatch parallel work via `Agent` instead, which **breaks every core invariant of this skill** (Lead-exclusive git, 1 task = 1 commit, contamination detection, Tester consolidation, Phase 2 simultaneous spawn). Loading once upfront removes that pressure.

If `ToolSearch` returns an error for any of these tool names, stop and report to the user via `AskUserQuestion` — do not proceed by substituting `Agent`. The substitution is not an alternative execution path; it is a failure mode.

### Lead's first actions (first 3-5 minutes)

1. **Parse the argument and grasp the user's intent**
   - The argument is exposed as `$ARGUMENTS` here (the raw text the user passed to `/agent-teams`). If `$ARGUMENTS` is empty, ask the user for the task description via `AskUserQuestion`.
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
3. **Identify the project's verification commands** — these will be substituted into spawn prompts so the skill stays language-/stack-agnostic. Determine each from the repository (`package.json` scripts, `pyproject.toml`, `Cargo.toml`, etc.) before Phase 2:
   - `<TEST_RUNNER_COMMAND>` — single-file/target unit test runner (e.g. `bun vitest run`, `pnpm vitest run`, `jest`, `pytest`, `cargo test --test`)
   - `<FULL_TEST_COMMAND>` — full unit-test suite (e.g. `bun run test:unit`, `pnpm test`, `pytest`, `cargo test`)
   - `<TYPECHECK_COMMAND>` — type checking (e.g. `bun --filter '*' typecheck && bun run typecheck`, `tsc -b`, `mypy .`, `cargo check`)
   - `<LINT_COMMAND>` — linting (e.g. `bun --filter '*' lint && bun run lint`, `eslint .`, `ruff check`, `cargo clippy`)
   - `<UNIT_TEST_FRAMEWORK>` — the framework Implementers should author tests in (e.g. Vitest, Jest, Pytest, Rust's built-in test)
4. **Decide the team composition** (see "Deciding the team composition" below)
5. **Decide the Wave structure** (typical: 4 in parallel + 2 blocked_by; details in `assets/wave-template.md`)
6. **Present the plan to the user → get approval → proceed to Phase 2 spawn**

Do not silently execute `TeamCreate` / `TaskCreate` / spawn without approval — these are large operations, so confirming user intent is mandatory.

## Required Roles

Every task needs the following roles. Whether they are dedicated or combined depends on scale, but no role may be omitted.

| Role | Canonical handle (`SendMessage` target) | Primary responsibilities |
|------|------------------------------------------|--------------------------|
| **Team Lead** (you) | `team-lead` | Task splitting, progress tracking, integration, final decisions, **exclusive execution of `git add` (per-path) and `git commit` (no amend)** |
| **Implementer** (≥1) | `impl-<area><N>` (e.g. `impl-doc1`, `impl-api2`) | Feature implementation, unit test authoring, local verification (`<TEST_RUNNER_COMMAND>` / `<TYPECHECK_COMMAND>` / `<LINT_COMMAND>`) → request commits from the Lead |
| **Reviewer** | `reviewer-code` | Code review, spec compliance, security review (when combined) |
| **Tester** | `tester-regression` | One final full regression run at the end of a wave |
| **Security Checker** | `security-checker` | Dedicated security review (may be combined with Reviewer depending on conditions) |

The handle column is the literal value passed to `Agent({ name: "<handle>", … })` at spawn time, and the same value Lead uses as `SendMessage({ to: "<handle>", … })`. Implementer handles follow `impl-<area><N>` where `<area>` matches the wave's scope prefix (D / A / AI / UI) and `<N>` is the per-area index (e.g. `impl-doc1`, `impl-doc2`, `impl-api1`).

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

1. **Split owners along file boundaries**: align task boundaries with file boundaries. When splitting "implement feature A", assign file X to `impl-area1` and file Y to `impl-area2`.
2. **Consolidate shared-file changes into one person**: if multiple tasks need to change the same file (e.g. index.ts, config, shared type definitions), consolidate edits to that file under a single teammate, or serialize them across Waves (via `TaskUpdate({ taskId, addBlockedBy: [...] })` — `TaskCreate` itself does not accept any `blocked_by` field, so dependencies are always wired post-creation) so they never run concurrently.
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
   - Prefer new helpers / high independence / no DB schema migration / no new dependencies
   - Verify they don't overlap with existing commits (search for similar task names with `git log --grep`)
3. **Decide the Wave structure** — typical is "4 in parallel + 2 blocked_by" (details: `assets/wave-template.md`):
   - Naming convention `W<n>-<D|A|AI|UI><id>` (D=doc / A=api / AI=ai / UI=ui)
   - Owner separation by file (1 file = 1 owner)
4. Present the plan (team composition + Wave structure + 6-task outline) to the user and get approval

### Phase 2: Create the team and spawn everyone at once

1. **TeamCreate** to make the team
2. Register each task with **TaskCreate** (one call per task), then **TaskUpdate** to wire dependencies
   - Dependencies are expressed via `TaskUpdate({ taskId, addBlockedBy: [<upstream-id>, …] })`. `TaskCreate` itself accepts only `subject` / `description` / `activeForm` / `metadata` — there is no `blocked_by` field on `TaskCreate`
   - Aim for ~5-6 tasks per teammate
3. Remind the user to enable **Delegate mode (Shift+Tab)** (so the Lead doesn't hijack implementation)
4. **Spawn every role's teammate at once in Phase 2** (Implementer + Reviewer + Tester, plus Security Checker if needed) using the `Agent` tool with `team_name: "<team>"` and `name: "<handle>"` parameters so each spawned agent joins the team
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

#### Concrete Phase 2 sequence (pseudocode)

```
// 1. Create team
TeamCreate({ team_name: "issue-123-wave-1", description: "issue #123 wave 1" })

// 2. Register 6 tasks (TaskCreate takes only subject / description / activeForm / metadata)
const t1 = TaskCreate({ subject: "[W1-D1] ...", description: "Owned files: ...", activeForm: "implementing ..." })
const t2 = TaskCreate({ subject: "[W1-D2] ...", ... })
const t3 = TaskCreate({ subject: "[W1-A1] ...", ... })
const t4 = TaskCreate({ subject: "[W1-A2] ...", ... })
const t5 = TaskCreate({ subject: "[W2-AI1] ...", ... })
const t6 = TaskCreate({ subject: "[W2-UI1] ...", ... })

// 3. Wire blocked_by AFTER creation (Wave 2 tasks blocked by all of Wave 1)
TaskUpdate({ taskId: t5.id, addBlockedBy: [t1.id, t2.id, t3.id, t4.id] })
TaskUpdate({ taskId: t6.id, addBlockedBy: [t1.id, t2.id, t3.id, t4.id] })

// 4. Spawn ALL teammates in a SINGLE message (multiple parallel Agent tool calls)
Agent({ team_name: "issue-123-wave-1", name: "impl-doc1",        subagent_type: "general-purpose", prompt: <filled implementer.md> })
Agent({ team_name: "issue-123-wave-1", name: "impl-doc2",        subagent_type: "general-purpose", prompt: <filled implementer.md> })
Agent({ team_name: "issue-123-wave-1", name: "impl-api1",        subagent_type: "general-purpose", prompt: <filled implementer.md> })
Agent({ team_name: "issue-123-wave-1", name: "impl-api2",        subagent_type: "general-purpose", prompt: <filled implementer.md> })
Agent({ team_name: "issue-123-wave-1", name: "reviewer-code",    subagent_type: "general-purpose", prompt: <filled reviewer.md>    })
Agent({ team_name: "issue-123-wave-1", name: "tester-regression", subagent_type: "general-purpose", prompt: <filled tester.md>     })
// + Agent({ ..., name: "security-checker", ..., prompt: <filled security-checker.md> }) when dedicated
```

##### Tightening teammate tool access via subagent definitions (optional)

The `subagent_type` you pass above may reference a project-/plugin-/user-level subagent defined at `.claude/agents/<name>.md` (or under a plugin). When the definition has a `tools:` frontmatter allowlist, the spawned teammate honors it — so you can structurally restrict a Reviewer/Tester to read-only tools (no `Edit` / `Write`) rather than relying only on prompt wording. Coordination tools (`SendMessage`, `Task*`) remain available to teammates even when other tools are restricted. This plugin does not currently ship subagent definitions; defining them in your own project gives you a second defensive layer.

### Phase 3: Execution and quality gates (continuous SendMessage interaction)

The Lead acts purely as an **orchestrator**. Never use the Edit tool on code (implementation belongs to Implementers). Only `git add` + `git commit` git operations are executed by the Lead on behalf of Implementers. When fixes are needed, always send a SendMessage to the Implementer.

#### Per-task cycle

```
1. Implementer self-claims a task and starts working
2. Implementer finishes implementation + local verification → SendMessage to Lead to request a commit
   (Request contents: file paths, counts (unit-test pass + typecheck/lint green), acceptance criteria, control-byte check `[]`, proposed commit message)
3. Lead checks scope with `git status` → runs `git add <per-path>` → `git commit -m "..."` on their behalf
4. Lead → SendMessage to Implementer: "commit <hash> done" → Implementer marks TaskUpdate completed
5. Lead → SendMessage to Reviewer (AND, if Security Checker is dedicated, to the Security Checker in parallel): "Please review commit <hash>, files: ..."
6. Reviewer (and Security Checker, if dedicated) reviews → each reports back to Lead via SendMessage
7. If there are Critical / Important / High findings (Reviewer uses Critical/Important/Minor, Security Checker uses Critical/High/Medium — treat **Critical/Important/High as must-fix**, Minor/Medium as follow-up):
   a. Lead → SendMessage to Implementer: "Please fix the following: ..."
   b. Implementer fixes → local verification → requests fix commit from Lead
   c. Lead runs the fix commit on their behalf (`fix(scope): #issue reviewer C-N ...`)
   d. Lead → SendMessage to Reviewer (and Security Checker, if they raised findings): "Please verify the fix"
   e. Reviewers re-check → repeat until OK
8. Tester is NOT called in this cycle (Implementer self-verification + Reviewer quality gate already establish commit-level quality)
9. Task N done → Implementer moves on to the next task
```

**The Tester is called exactly once at the end of the wave** (full regression). See `references/tester-optimization.md`.

#### Fix-cycle guardrails

The Reviewer/Security-Checker ↔ Implementer fix loop in step 7 can spiral if the same class of Critical / Important / High keeps recurring. To stop runaway loops:

- **Cap per task: `MAX_FIX_ITERATIONS = 3`** (each iteration = one Implementer fix + reviewers' re-check, counted across Reviewer and Security Checker findings combined for the same task)
- Lead tracks the iteration count per task locally (a small note table is enough; do **not** write it into the TaskCreate description because teammates also write there and race conditions clobber notes)
- If iteration 3 still produces Critical / Important / High on the same task:
  1. Lead halts the cycle and instructs the Reviewer (and Security Checker, if dedicated) to summarize the remaining findings
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
impl-doc1: task 1 implementation done → review pending → starts task 3
impl-doc2: implementing task 2
Reviewer: reviewing task 1

* But never run tasks that touch the same file in parallel.
```

#### Teammate unresponsiveness fallback (Implementer / Reviewer / Security Checker)

If an **Implementer** stops responding mid-wave (no progress, no answer to SendMessage):

- Send a status-check SendMessage. If still no reply after the expected response window, **spawn a replacement teammate** (`name: "impl-<area><N>-r"`, `r` = replacement) for the remaining owned tasks, hand off the in-progress task with explicit "what's done / what's left" context in the spawn prompt, then send `shutdown_request` to the original teammate.
- Do not run the unresponsive Implementer's pending edits yourself (that collapses the quality gate). The replacement does them.

**Reviewer** / **Security Checker** non-response is handled the same way (replacement spawn), but include an explicit "commits not yet reviewed: `<hash1>, <hash2>, …`" list in the replacement's spawn prompt so review context is reconstructed.

**Tester** non-response uses the Lead direct-verification route instead (see `references/tester-optimization.md`) — Tester replacement is rarely useful because the regression is read-only.

Public docs limitation: teammates sometimes fail to mark tasks as `completed`, which blocks downstream `addBlockedBy` tasks. If `TaskList` shows a task stuck in `in_progress` after the Implementer has clearly finished (commit landed + Reviewer PASS), the Lead may `TaskUpdate({ taskId, status: "completed" })` directly — citing the commit hash as evidence in a SendMessage to the Implementer ("marking <task> completed on your behalf — commit <hash> landed and reviewer PASS"). Treat this as a tracking correction, not a workflow shortcut.

### Phase 4: Disband (Wave completion → TeamDelete)

```
1. Lead confirms all tasks are completed and all Reviewer (and Security Checker, if dedicated) PASS
2. Lead → SendMessage to Tester to request the final full regression (once only)
3. On Tester PASS, send shutdown_request individually to each teammate; wait for shutdown_approved from each
4. Once every teammate has shutdown_approved (or the team has confirmed teammate_terminated), call TeamDelete
5. Report a wave summary to the user
```

Notes on Phase 4:
- `shutdown_request` is a one-per-teammate SendMessage (not a broadcast). Example: `SendMessage({ to: "impl-doc1", message: { type: "shutdown_request", reason: "wave complete" } })`. Teammates respond with `shutdown_response` (`approve: true|false`); on approve they exit.
- If a teammate `rejects` (e.g. they believe a task is unfinished), the Lead inspects the reason, confirms task status, and re-sends after resolving — do not force-cleanup a rejecting teammate.
- **`TeamDelete` fails if any teammate is still active** (per Agent Teams runtime). Confirm all `teammate_terminated` notifications before calling. The detailed checklist (`assets/lead-checklist.md` "On disband") enumerates the per-teammate verification steps.
- If the Tester takes longer than 3× its expected time (~6 min for a typical ~1-2 min run) without responding, the Lead may run verification commands directly via Bash (Lead direct-verification route, details: `references/tester-optimization.md`). This is read-only objective verification and does not bypass the quality gate.

For a detailed checklist, see `assets/lead-checklist.md`.

## Things you must not do

### Skill-active `Agent`-tool prohibition (overrides the global parallelism rule)

- **Use the `Agent` tool to dispatch parallel implementation / review / test / security work outside the team mechanism while this skill is active**: all parallelism in this skill MUST go through `TeamCreate` + `TaskCreate` + teammate dispatch (and SendMessage interaction). The global "Parallel Execution for Speed" directive — "2+ independent subtasks → parallel `Agent` calls" — is **explicitly overridden for the duration of this skill**. The agent-teams flow IS the parallelism mechanism here; routing around it via free-form `Agent` calls defeats every quality gate (Reviewer, Tester, Security Checker) and the Lead's exclusive git control, and structurally re-introduces the race conditions this skill was built to eliminate.
  - **What counts as "team-spawn dispatch" (allowed)**: `Agent({ team_name, name, subagent_type, prompt, … })` invocations whose purpose is to spawn a teammate that joins the team. These are the Phase 2 spawn calls described in the Workflow above; they are not "free-form `Agent` calls".
  - **What counts as "free-form `Agent` calls" (forbidden once `TeamCreate` is done)**: any `Agent` invocation without `team_name` (i.e. not joining the team) for implementation, review, test, or security work. From **Phase 2 onward (TeamCreate done), free-form `Agent` invocations are forbidden** without exception.
  - Allowed exception (Phase 1 only): the Lead may use `Agent` with `subagent_type: Explore` for **read-only** investigation (issue lookup, code exploration, doc search) to shorten Phase 1 planning. This is read-only and bypasses no quality gate.
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
- **Run destructive git operations other than `add` (per-path) / `commit` (no amend)**: forbidden even for the Lead. The canonical list of "everything beyond `add` / `commit`" lives in the "Lead's git permissions" section above and in `references/git-permissions.md`; consult one of those rather than relying on memory. Trying to "clean things up" with a destructive operation causes history-destruction incidents. When such an operation is genuinely needed, ask the user to run it manually via AskUserQuestion
- **Bundle multiple tasks into one commit**: strict "1 task = 1 commit". A commit that mixes tasks ends up with a commit message that can only mention one of them, and splitting it later requires destructive operations
- **Do "leftover work" after disbanding the team**: every piece of work must be completed by a teammate. The Lead doing "the final polish" collapses the quality gate
  - Exception: when the Tester becomes unresponsive, the Lead may run read-only verification commands (the project's `<FULL_TEST_COMMAND>` / `<TYPECHECK_COMMAND>` / `<LINT_COMMAND>`) on its behalf — this does not count as bypassing the quality gate (see `references/tester-optimization.md`)

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

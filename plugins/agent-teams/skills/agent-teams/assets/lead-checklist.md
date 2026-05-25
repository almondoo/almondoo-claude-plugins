# Lead checklist

What the Lead should verify at each phase of the wave. Consult at wave start / during commit proxying / at wave completion / on disband.

## Wave start (before Phase 1 + Phase 2 spawn)

- [ ] Understand the user's request and grasp the overall scope
- [ ] Read the issue / spec / git log and pick 6 target tasks from the backlog
  - [ ] Prefer new helpers / high independence / no Prisma migration / no new dependencies
  - [ ] Confirm no overlap with existing commits (search similar task names via `git log --grep`)
- [ ] Decide the Wave structure (typical: 4 in parallel + 2 blocked_by)
- [ ] Follow the naming convention `W<n>-<D|A|AI|UI><id>`
- [ ] Decide the owner-separation strategy (1 file = 1 owner)
- [ ] Present the plan (team composition + Wave structure + 6-task outline) to the user and get approval

## During Phase 2 spawn

- [ ] Create the team via `TeamCreate`
- [ ] Register 6 tasks via `TaskCreate` (each description states owned files / forbidden files / acceptance criteria / commit-message draft)
- [ ] Wire Wave 2 dependencies via `TaskUpdate({ taskId, addBlockedBy: [<upstream-id>, …] })` after each task is created (`TaskCreate` itself takes only `subject` / `description` / `activeForm` / `metadata`, no `blocked_by` field)
- [ ] Copy templates from `assets/spawn-prompts/` and substitute placeholders
- [ ] **Spawn 6 teammates in a single message** (Implementer×4 + Reviewer + Tester)
  - Add a Security Checker if needed (large or security-critical)
- [ ] State explicitly in spawn prompts that Reviewer / Tester "wait for SendMessage"
- [ ] Confirm Delegate mode (Shift+Tab) is enabled

## During commit proxying (each time an Implementer requests a commit)

- [ ] Confirm the Implementer's request:
  - [ ] Owned file paths (per-path, no off-target contamination)
  - [ ] unit-test counts / typecheck / lint green (per the project's `<TEST_RUNNER_COMMAND>` / `<TYPECHECK_COMMAND>` / `<LINT_COMMAND>`)
  - [ ] **literal control-byte check** reports `[]`
  - [ ] Proposed commit message follows the convention
- [ ] Check the working tree with `git status`
  - [ ] The Implementer's 2 owned files are in Untracked (other teammates' untracked may coexist; they won't contaminate unless staged)
- [ ] **`git add` with per-path** (absolutely no `-A` / `.` / `-u`)
- [ ] Re-check with `git status` to confirm staging contains exactly the 2 owned files
- [ ] Run `git commit -m "..."` (no `--amend`, no push)
- [ ] SendMessage the Implementer: "commit <hash> done, please TaskUpdate completed"
- [ ] SendMessage the Reviewer to request a review

## When Reviewer results arrive

- [ ] If there are Critical / Important:
  - [ ] SendMessage the Implementer with a fix request (cite specific file:line + fix proposal)
  - [ ] On Implementer fix completion → run the fix commit via the proxy procedure above
  - [ ] SendMessage the Reviewer for a re-review
  - [ ] Repeat until Critical/Important is zero
- [ ] On PASS:
  - [ ] Minor items don't require fixes in this PR; tell the Implementer they'll be follow-ups
  - [ ] Proceed to the next task or wave completion

## Wave completion (after all tasks completed + all Reviewer PASS)

- [ ] **SendMessage the Tester to request the final full regression** (once only)
  - [ ] `<FULL_TEST_COMMAND>` (e.g. `bun run test:unit`, `pnpm test`, `pytest`)
  - [ ] `<TYPECHECK_COMMAND>` (e.g. `bun --filter '*' typecheck && bun run typecheck`, `tsc -b`, `mypy .`)
  - [ ] `<LINT_COMMAND>` (e.g. `bun --filter '*' lint && bun run lint`, `eslint .`, `ruff check`)
  - [ ] `git log --stat` to confirm per-commit staging
- [ ] On Tester PASS → proceed to disband
- [ ] **If no response after 3× the Tester's expected time (~6 min vs ~1-2 min)**:
  - [ ] One status-check ping
  - [ ] One re-request
  - [ ] If still no response, **switch to the Lead direct-verification route** (details: `references/tester-optimization.md`)
- [ ] On FAIL, request fixes from the Implementer → re-regression

## On disband

- [ ] Send **individual shutdown_request via SendMessage** to every teammate
- [ ] Wait for shutdown_approved from each teammate
- [ ] Confirm `teammate_terminated` notifications from system
- [ ] All shut down (or even if some are unresponsive, `TeamDelete` force-cleans them)
- [ ] Run `TeamDelete`
- [ ] Confirm final state with `git log main..HEAD --oneline | head` + `git status`
- [ ] Report wave summary to the user:
  - [ ] N commits added (per-commit listing + contents)
  - [ ] Test count / typecheck / lint results
  - [ ] Any incidents / fixes (literal control bytes / git-reset violations etc.)
  - [ ] State push not performed (the Lead never pushes — the user runs `git push` manually after reviewing the wave)

## Reminders for forbidden actions (Lead easily forgets)

- ❌ Edit / Write on code (implementation belongs to Implementers)
- ❌ `git reset` / `--amend` / `git restore` / `git push` etc. (only `add` / `commit`)
- ❌ Bundling multiple tasks into one commit
- ❌ Per-commit verification requests to the Tester
- ❌ Spawning Reviewer / Tester mid-wave (all spawn at Phase 2)
- ❌ Moving forward without waiting for teammate responses (race / consistency damage)
- ❌ Doing "final polish" after disbanding the team (collapse of the quality gate)

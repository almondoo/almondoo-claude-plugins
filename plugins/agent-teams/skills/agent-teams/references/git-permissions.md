# Lead's git permissions — detailed reference

Detailed version of "Lead's git permissions" in SKILL.md. Classifies every git operation as destructive vs non-destructive, and states each role's permissions explicitly.

## Design principle

Classify git operations as **destructive** (irreversibly mutate history / working tree / staging) vs **non-destructive** (read / fetch / temporary stash / new-additions only).

- **Among destructive operations, the only ones the Lead may execute are `git add` (per-path) and `git commit` (no amend)**
- All other destructive operations are forbidden even for the Lead
- Non-destructive operations are free for every teammate

## Why even the Lead is forbidden anything beyond `add` / `commit`

- **Race-condition prevention**: when multiple teammates run `git add` / `git commit` concurrently in the same working tree, they pull in another teammate's untracked / staged files, violating "1 task = 1 commit" and contaminating with off-target files
- **Structural elimination of destructive operations**: history-destroying operations like `git reset` / `--amend` / `git restore` reduce mistaken executions to zero only by removing the "Lead may execute it as an exception" loophole
  - Real incident: running `git reset HEAD~1` twice in a shared workspace caused another teammate's commit to disappear from history
- **Commit-message consistency**: with the Lead executing commits, project conventions (Conventional Commits / "1 task = 1 commit") are uniformly enforced
- **Preventing off-target file contamination**: the Lead can tighten staging scope by checking with `git status` → running `git add <per-path>`

## Destructive git operations — full table (Lead may execute only `add` / `commit`)

| Operation | Lead allowed? | Note |
|-----------|---------------|------|
| `git add <per-path>` | ✅ Lead exclusive | `-A` / `.` / `-u` forbidden; always specify paths |
| `git commit -m "..."` | ✅ Lead exclusive | `--amend` forbidden; stack a new commit instead |
| `git commit --amend` | ❌ Forbidden even for Lead | History destruction |
| `git reset` (--hard / --soft / --mixed) | ❌ Forbidden even for Lead | History destruction; risk of rolling back others' commits |
| `git restore` / `git checkout <file>` (discard uncommitted) | ❌ Forbidden even for Lead | Work destruction |
| `git push` / `git push --force` | ❌ Forbidden even for Lead | Remote impact; the project's CLAUDE.md must keep push out of Lead authority |
| `git rebase` / `git merge` | ❌ Forbidden even for Lead | History manipulation; conflict resolution turns destructive |
| `git revert` / `git cherry-pick` | ❌ Forbidden even for Lead | Commit operation (outside add / commit scope) |
| `git stash drop` / `stash clear` | ❌ Forbidden even for Lead | Permanent deletion of stashed contents |
| `git branch -D` / `git branch -d` | ❌ Forbidden even for Lead | Branch deletion |
| `git tag -d` | ❌ Forbidden even for Lead | Tag deletion |
| `git clean -f` / `-d` | ❌ Forbidden even for Lead | Destruction of untracked files |
| `git config` (write) | ❌ Forbidden even for Lead | Environment change |
| `git worktree remove` | ❌ Forbidden even for Lead | Worktree destruction |

When a ❌ operation becomes genuinely necessary (contamination / accident / merge etc.), the Lead **must obtain user approval via AskUserQuestion and have the user run it manually**. The Lead never runs it.

## Non-destructive git operations — full table (free for every teammate)

| Category | Operation |
|----------|-----------|
| Read | `git status` / `git log` / `git diff` / `git show` / `git blame` / `git reflog` / `git ls-files` / `git rev-parse` |
| List | `git branch -v` / `git branch -a` / `git tag -l` / `git remote -v` / `git stash list` / `git worktree list` |
| Fetch (only updates local refs from remote) | `git fetch` / `git remote update` |
| Stash / restore | `git stash push` / `git stash pop` / `git stash apply` / `git stash show` |
| New-additions (no destruction of existing state) | `git branch <new>` / `git switch -c <new>` / `git tag <new>` (unless pushed) / `git worktree add` |

However, **any decision to perform a destructive operation must be escalated to the Lead via SendMessage** (from the Implementer side) or **via AskUserQuestion** (from the Lead side).

## What if an Implementer notices contamination

Do not try to "fix it" with `git reset` / `--amend`. **Always consult the Lead via SendMessage**. The Lead picks one of the following (all within `add` / `commit` scope):

- **If the functionality is correct**: accept it and follow up as a separate issue (no remote impact since push hasn't happened; no destructive operation needed)
- **If the functionality is wrong**: ask the Implementer for a new fix commit (`fix(scope): #issue ...`)
- **If we really must roll back**: ask the user via AskUserQuestion to run `git revert` / `git reset` etc. manually (the Lead does not execute it)

## Implementer workflow

1. Implementation done → local verification (`<TEST_RUNNER_COMMAND>` / `<TYPECHECK_COMMAND>` / `<LINT_COMMAND>`) returns green
2. SendMessage to the Lead to **request a commit**:
   ```
   [W1-D1 commit request ready]
   - Owned files: lib/<your-module>/.../foo.ts + __tests__/foo.unit.test.ts
   - Counts: N tests pass / typecheck & lint green
   - Acceptance criteria: all ✓
   - Proposed commit message: feat(<scope>): #<issue> ...
   ```
3. Lead verifies scope with `git status` → runs `git add <per-path>` → `git commit -m "..."` on their behalf
4. On receiving "commit <hash> done" from the Lead → TaskUpdate completed → next task

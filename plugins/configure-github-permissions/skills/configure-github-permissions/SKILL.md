---
name: configure-github-permissions
description: Interactively configure GitHub CLI (gh) permissions in the project's `.claude/settings.local.json` by asking the user category-by-category which gh operation groups should be `allow` / `ask` / `deny`. Use when the user wants to set up gh permissions, reduce gh prompt frequency, allowlist GitHub commands, configure which gh operations are auto-allowed, blocked, or prompt-on-use, or mentions setting up gh allowlist / permission tier / per-category permissions for a project. Walks through 10 categories (read-only, local ops, comment, issue create/edit, issue close, pr create/edit, pr merge/close, release, workflow run, gh api) via AskUserQuestion, then merges the resulting `Bash(gh ...)` entries into `permissions.{allow,ask,deny}` without duplication.
---

# Configure GitHub Permissions

## Overview

A skill that configures `gh` command permissions in the project's `.claude/settings.local.json` at **per-category granularity**. It walks the user through 10 categories × 3 choices (`allow` / `ask` / `deny`) via AskUserQuestion and routes each answer into `permissions.allow` / `permissions.ask` / `permissions.deny`.

**Why category-grained?** To support real-world policies like *"auto-allow all read-only operations, but explicitly deny irreversible operations such as close / merge / release."* A coarse tier-based selector cannot express this — choosing `allow` for the read tier would also force the same setting on the comment tier. This skill lets the user decide each category independently.

**Design principles:**
- Each category accepts one of `allow` (auto-execute), `ask` (prompt every time), `deny` (auto-block).
- Categories that match the user's global CLAUDE.md Tier 3 rule (destructive / irreversible external writes) **default to `deny`**.
- Existing `allow` / `ask` / `deny` entries are preserved; no duplicate writes.
- If the same pattern already exists in another array, it is treated as a **conflict** and confirmed with the user before writing.

## When to Use

- The user says "I want to configure `gh` permissions" or "add to the allowlist".
- The user says "I want fine-grained allow/ask/deny per category".
- A new project is being set up and `gh issue view` etc. prompt every time.
- A `fewer-permission-prompts`-style request targets `gh` operations.
- The user wants to explicitly block destructive operations (merge / release delete / etc.).

## Categories

10 categories × 3 choices (allow / ask / deny). The commands and recommended defaults are below.

### Cat 1 — Read-only: All read-only operations (recommended: allow)

```
Bash(gh issue view:*)        Bash(gh issue list:*)        Bash(gh issue status:*)
Bash(gh pr view:*)           Bash(gh pr list:*)           Bash(gh pr status:*)
Bash(gh pr diff:*)           Bash(gh pr checks:*)
Bash(gh repo view:*)         Bash(gh repo list:*)
Bash(gh release view:*)      Bash(gh release list:*)
Bash(gh run view:*)          Bash(gh run list:*)
Bash(gh workflow view:*)     Bash(gh workflow list:*)
Bash(gh search:*)            Bash(gh label list:*)
Bash(gh auth status:*)
```

### Cat 2 — Local ops: Local operations (recommended: allow)

```
Bash(gh pr checkout:*)
Bash(gh browse:*)
```

`gh browse` only opens a browser and performs no writes. `gh pr checkout` only creates a local branch.

### Cat 3 — Comments & reviews: Sending comments and reviews (recommended: ask)

```
Bash(gh issue comment:*)
Bash(gh pr comment:*)
Bash(gh pr review:*)
```

These produce externally visible statements, but they can be edited or deleted afterward and the retraction cost is low. Still, the user often wants to confirm the content before sending, so the recommendation is `ask`.

### Cat 4 — Issue create / edit: Issue creation and editing (recommended: ask)

```
Bash(gh issue create:*)
Bash(gh issue edit:*)
```

### Cat 5 — Issue close / reopen: Closing and reopening issues (recommended: deny)

```
Bash(gh issue close:*)
Bash(gh issue reopen:*)
```

`gh issue close` is listed in the global CLAUDE.md Tier 3 rule as a "destructive / irreversible write to external systems". Closing fires external notifications (email / Slack integrations / GitHub Actions triggers) that reach every subscriber, making it effectively unretractable. The default is `deny`. Repositories that use issues as an internal task tracker (where the close notification is low-stakes) can override this on a per-repository basis via their CLAUDE.md. `reopen` is not destructive on its own, but pairing it with `close` keeps the operational policy simple.

### Cat 6 — PR create / edit: PR creation and editing (recommended: ask)

```
Bash(gh pr create:*)
Bash(gh pr edit:*)
Bash(gh pr ready:*)
```

### Cat 7 — PR merge / close: PR merging and closing (recommended: deny)

```
Bash(gh pr merge:*)
Bash(gh pr close:*)
```

These commands fall under global CLAUDE.md Tier 3. Merges are effectively irreversible and `close` fires notifications. The default is `deny`.

### Cat 8 — Release ops: Release creation, editing, and deletion (recommended: deny)

```
Bash(gh release create:*)
Bash(gh release edit:*)
Bash(gh release upload:*)
Bash(gh release delete:*)
Bash(gh release delete-asset:*)
```

Public artifact releases carry an extremely high retraction cost.

### Cat 9 — Workflow execution: Workflow run / enable / disable (recommended: deny)

```
Bash(gh workflow run:*)
Bash(gh workflow enable:*)
Bash(gh workflow disable:*)
Bash(gh run rerun:*)
Bash(gh run cancel:*)
```

Re-running, canceling, or toggling CI workflows has large side effects.

### Cat 10 — gh api low-level: `gh api` low-level invocations (recommended: ask)

```
Bash(gh api:*)
```

`gh api` switches HTTP methods via the `-X` flag and data flags (`-f` / `-F` / `--input`), so Bash permission argument-pattern matching cannot reliably isolate the method or its destructiveness. The official Claude Code documentation (`code.claude.com/docs/en/permissions`) also states **"Bash permission patterns that try to constrain command arguments are fragile"**. Bypass paths are numerous: flag reordering (`gh api foo -X DELETE` ⇄ `gh api -X DELETE foo`), the `=` form `--method=DELETE`, automatic POST promotion when `-f` is added, body submission via `--input file`, etc.

That said, there are legitimate GET-only use cases that **only** `gh api` can cover. Representative examples:

- **PR review comments (inline comments on specific diff lines)**: `gh pr view` cannot fully retrieve them; `gh api repos/{owner}/{repo}/pulls/{N}/comments` is required.
- Specific metadata (custom properties, triage status, issue reaction breakdowns).

Therefore a blanket `deny` would stop everyday read tasks like PR review tracking and issue metadata retrieval. The default is **`ask`**, with the operational expectation that the user visually verifies the endpoint and method at invocation time.

If `ask` becomes noisy, the recommended approach is to add **path-scoped allow rules for specific GET endpoints** the user hits frequently (e.g. `Bash(gh api repos/{owner}/{repo}/pulls/*/comments)`). The skill cannot ship such rules as defaults; the user adds them manually.

## Step-by-step

### Step 1: Locate settings.local.json

```bash
git rev-parse --show-toplevel
```

The target is that path + `/.claude/settings.local.json`. Read the existing content with the `Read` tool. If the file does not exist, treat it as a fresh-write. If the working directory is not inside a git repository, `git rev-parse` will fail; in that case fall back to the current directory and inform the user.

### Step 2: Parse existing permissions

Read the three arrays `permissions.allow` / `permissions.ask` / `permissions.deny`. Entries already in those arrays are treated as "previously configured by the user" and preserved.

### Step 3: Ask the 10 categories via AskUserQuestion batches

**Always use AskUserQuestion** (asking via plain text is prohibited). AskUserQuestion accepts at most 4 questions per message, so split the 10 categories into **3 batches**:

**Batch 1** (4 questions):
1. Cat 1 — Read-only
2. Cat 2 — Local ops
3. Cat 3 — Comments & reviews
4. Cat 4 — Issue create/edit

**Batch 2** (4 questions):
5. Cat 5 — Issue close/reopen
6. Cat 6 — PR create/edit
7. Cat 7 — PR merge/close
8. Cat 8 — Release ops

**Batch 3** (2 questions):
9. Cat 9 — Workflow execution
10. Cat 10 — gh api low-level

Each question takes this shape:

- **question**: `How should the gh commands in "<category-name>" be handled? (Concrete commands: gh xxx, gh yyy, ...)`
- **header**: A short identifier for the category (max 12 chars, e.g. `Read-only`, `PR merge`, `gh api`).
- **multiSelect**: `false`
- **options**: 3 entries. **Put the recommended choice first and append `(recommended)` to its label.**
  - `Auto-allow (allow)` — execute without a prompt every time.
  - `Ask every time (ask)` — prompt before execution.
  - `Auto-deny (deny)` — block execution.

### Step 4: Route the answers into allow / ask / deny

For each category's selected choice, place every command pattern in that category as a candidate for the corresponding array. Union with the existing array and extract **only the new additions**.

### Step 5: Conflict check

If a new entry to be added already exists in a different array (e.g. trying to add to `allow` while it already sits in `deny`), it is a **conflict**.

For each conflict, ask via AskUserQuestion (singly or batched per message):

- question: `"Bash(gh xxx:*)" is already in deny. Move it to allow?`
- options:
  - `Keep existing deny` (drop the new allow)
  - `Remove from deny and move to allow`
  - `Keep both` (Claude Code generally prioritizes deny; explain in the description that effective behavior does not change)

### Step 6: Preview confirmation before writing

Use `AskUserQuestion` for a final confirmation:

- The question body must include:
  - The full target path to be written to.
  - The list of new `allow` entries being added.
  - The list of new `ask` entries being added.
  - The list of new `deny` entries being added.
  - Any entries that conflict resolution will remove.
- options:
  - `Write as previewed` (recommended)
  - `Cancel`

**If 0 entries are added and 0 are removed**, skip the prompt, tell the user "Everything is already configured" and exit.

### Step 7: Write the file

- File exists: use `Edit` to update only the array members of `permissions.allow` / `permissions.ask` / `permissions.deny`. Do not touch other keys (e.g. `enabledPlugins`) or comments.
- File does not exist, or has no `permissions` key: use `Write` to create this minimal scaffolding:

```json
{
  "permissions": {
    "allow": [ ... ],
    "ask": [ ... ],
    "deny": [ ... ]
  }
}
```

**Omit empty arrays** (if you only add to `allow` and `ask` / `deny` end up empty, omit those keys entirely).

- 2-space indent, trailing newline.
- If `.claude/` does not exist, run `mkdir -p .claude` first.

After writing, report the per-array additions (e.g. `allow +5, ask +3, deny +7`) and the write path in 1–2 sentences and exit.

## Edge cases

- **Corrupted JSON**: If the `Read` content cannot be parsed (equivalent to `JSON.parse` failure), tell the user "Fix the JSON syntax error in `.claude/settings.local.json` first and re-run" and abort. Do not rewrite blindly.
- **Patterns from the same category are scattered across multiple arrays**: treat as a conflict and resolve in Step 5.
- **Monorepo / not a git repository**: if `git rev-parse --show-toplevel` fails, fall back to the current directory and inform the user.
- **`.claude/` does not exist**: the `Write` tool does not auto-create parent directories, so run `mkdir -p .claude` first.
- **User cancels mid-batch**: do not proceed to Step 4 with only partially collected answers. The policy is to **gather all categories before writing**. On a mid-batch cancellation, tell the user "Aborting. Nothing has been written." and exit.
- **User says "all ask is fine"**: do not skip the per-category questions. As a shortcut, you may offer "do you want a global all-deny / all-ask / all-allow option?" only if the user explicitly asks, and present it via AskUserQuestion before the category-by-category flow. The default remains the fine-grained per-category flow.

## Why this design

- **Fine-grained 3-choice**: A tier selector cannot express "allow most things but keep one slice on ask", so the skill directly asks for category × {allow,ask,deny}.
- **AskUserQuestion throughout**: The user's global CLAUDE.md requires every confirmation to go through AskUserQuestion.
- **Destructive categories default to deny**: Merge / release / workflow execution / `gh api` fall under Tier 3. The skill must not recommend auto-allow for these.
- **Do not break existing state**: No duplicate writes, preserve ordering of existing entries, do not touch keys outside `permissions` — otherwise the user can no longer trust the settings file as a whole.
- **Surface conflicts explicitly**: If `allow` and `deny` would both contain the same entry, do not silently drop one. Ask. The goal is to keep the settings file trustworthy.

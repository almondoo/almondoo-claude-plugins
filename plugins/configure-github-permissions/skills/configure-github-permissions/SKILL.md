---
name: configure-github-permissions
description: Interactively configure GitHub CLI (`gh`, including `gh api`) AND `git` command permissions in the **project-local** `.claude/settings.local.json` (not the committed `.claude/settings.json`, not the user-global `~/.claude/settings.json`) by asking the user category-by-category which command groups should be `allow` / `ask` / `deny`. Use when the user wants to set up gh or git permissions, reduce gh / git prompt frequency, allowlist GitHub or git commands, configure which gh / git operations are auto-allowed, blocked, or prompt-on-use, mentions "too many gh prompts" / "too many git prompts", says "edit settings.local.json for gh" / "organize gh permissions" / "auto-approve gh" / "set up git permissions" / "configure git allowlist" / "allowlist git commands" / "block git push for this project", or mentions setting up a gh / git allowlist / permission tier / per-category permissions for a project. Walks through 17 categories — gh (read-only, local ops, comment, issue create/edit, issue close, pr create/edit, pr merge/close, release, workflow run, gh api, delete-class) and git (read-only, local writes, history rewrite, tag, destructive local, push) — via AskUserQuestion, then merges the resulting `Bash(gh ...)` and `Bash(git ...)` entries into `permissions.{allow,ask,deny}` without duplication. Prefer this skill over `fewer-permission-prompts` when the user wants an upfront category-based setup rather than transcript-driven cleanup; prefer this over `update-config` when the target is specifically `gh` / `git`, not arbitrary commands.
---

# Configure GitHub (gh) and Git Permissions

## Overview

A skill that configures `gh` AND `git` command permissions in the project's `.claude/settings.local.json` at **per-category granularity**. It walks the user through 17 categories × 3 choices (`allow` / `ask` / `deny`) via AskUserQuestion and routes each answer into `permissions.allow` / `permissions.ask` / `permissions.deny`. Categories 1–11 cover `gh`; categories 12–17 cover `git`.

**Why category-grained?** To support real-world policies like *"auto-allow all read-only operations, but explicitly deny irreversible operations such as merge / release / push / hard-reset."* A coarse tier-based selector cannot express this — choosing `allow` for the read tier would also force the same setting on the comment tier. This skill lets the user decide each category independently.

**Why bundle `gh` and `git`?** Both surface the same kinds of irreversibility problems (remote write, history rewrite, force-overwrite local state) and the user is usually adjusting both together. Splitting into two skills would duplicate the merge / dedupe / preview machinery and force the user to run two wizards back-to-back.

**Why `.claude/settings.local.json` and not `.claude/settings.json`?** The skill targets the **gitignored** local file so that per-developer `gh` permission tweaks do not leak into the team's committed policy. Teams that want a shared baseline should hand-edit `.claude/settings.json` after agreeing on it; this skill stays out of that file. The user-global `~/.claude/settings.json` is also out of scope — it represents cross-project defaults and should be edited deliberately by the user.

**Design principles:**
- Each category accepts one of `allow` (auto-execute), `ask` (prompt every time), `deny` (auto-block).
- Categories that match the user's global CLAUDE.md Tier 3 rule (destructive / irreversible external writes) **default to `deny`**.
- Existing `allow` / `ask` / `deny` entries are preserved; no duplicate writes.
- If the same pattern already exists in another array, it is treated as a **conflict** and confirmed with the user before writing.
- For git, several categories use **broad allow + narrow deny** so that one broad pattern (e.g. `Bash(git branch:*)`) can cover read-style usage while destructive sub-uses (`Bash(git branch -D:*)`) are blocked by a paired entry in the destructive category. This works because Claude Code evaluates rules in the order **deny → ask → allow with first-match-wins** (`code.claude.com/docs/en/permissions`), so the narrower deny overrides the broader allow.

## When to Use

- The user says "I want to configure `gh` permissions" / "configure git permissions" / "add to the allowlist".
- The user says "I want fine-grained allow/ask/deny per category" for `gh` or `git`.
- A new project is being set up and `gh issue view` / `git status` etc. prompt every time.
- A `fewer-permission-prompts`-style request targets `gh` or `git` operations.
- The user wants to explicitly block destructive operations (merge / release / `git push` / `git reset --hard` / etc.).

## When NOT to Use

- **The user's global `~/.claude/settings.json` already covers their `gh` / `git` usage** and project-local override is not needed. Running the skill in that case mostly produces 0-addition runs and pads `.claude/settings.local.json` with entries the global policy already handles. Tell the user to inspect `~/.claude/settings.json` first.
- **No `gh` / `git` prompts are firing in practice.** Pre-emptively populating 17 categories worth of allow/ask/deny for verbs the user never invokes creates dead config without value. Wait until the user is actually friction-bound.
- **The user wants a one-off tweak to a single verb** (e.g. "just allow `gh pr view`" or "just deny `git push`"). Hand-edit `.claude/settings.local.json` or use the `update-config` skill — running a 17-category wizard for one entry is disproportionate.
- **The user wants a team-shared policy** committed into `.claude/settings.json`. The skill is hard-fixed to the gitignored local file. Edit the committed file by hand after the team agrees.

## Default selection logic

The recommended default for each category is derived from four rules. The same logic should be used to decide the default of any new category added in the future, including the `git` categories.

1. **Pure-read, no side effects → `allow`.** Read-only verbs (`gh ... view` / `list` / `status` / `diff` / `checks` / `search`; `git status` / `diff` / `log` / `show` / `blame` / `ls-files`) and locally-scoped no-op verbs (`gh pr checkout`, `gh browse`, `git switch <branch>`, `git fetch`) cannot mutate remote state, so prompting on them is pure friction.
2. **External-visible but reversible → `ask`.** Verbs that produce subscriber-visible side effects (gh comments, reviews, issue create / close / reopen, PR create / edit / ready) OR that rewrite shared local history in a way that's hard to undo without remembering SHAs (`git merge`, `git rebase`, `git cherry-pick`, `git revert`, `git reset --soft|--mixed`, `git tag`) can be edited or rolled back after the fact, so per-invocation user verification is the right balance between safety and friction.
3. **Effectively irreversible external write → `deny`.** Verbs the user's global CLAUDE.md treats as Tier 3 (gh PR merge / close, release create / edit / delete, repo delete, issue delete, `git push` / `git push --force`) must not be auto-allowed by any project policy. Side-effect-heavy verbs with large blast radius (gh workflow run / enable / disable / cancel, run rerun) and locally-destructive verbs that cannot be undone (`git reset --hard`, `git restore`, `git checkout -- *`, `git branch -D`, `git clean -fd`, `git stash drop`/`clear`) follow the same rule.
4. **Argument-pattern matching is fragile → `ask`.** `gh api` switches HTTP methods via `-X` and data flags, and Bash permission patterns cannot reliably isolate the method. The skill cannot ship a path-scoped allowlist as a default, so the safe baseline is per-invocation prompt.

When a category sits between two rules (e.g. `gh issue close` is Tier 2 but fires external notifications), prefer the **less destructive** default (here: `ask`, not `deny`) and let the user override via this skill's per-category prompt or via their own CLAUDE.md.

## Categories

17 categories × 3 choices (allow / ask / deny). Cat 1–11 cover `gh`; Cat 12–17 cover `git`. The commands and recommended defaults are below.

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

### Cat 5 — Issue close / reopen: Closing and reopening issues (recommended: ask)

```
Bash(gh issue close:*)
Bash(gh issue reopen:*)
```

Reversible via `gh issue reopen`, so Tier 2 in global CLAUDE.md (not Tier 3). Default `ask` lets the user eyeball the issue number before sending. Tighten to `deny` on public OSS repos where even a transient close ping is high-cost. `reopen` is grouped with `close` to keep the policy simple.

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

Re-running, canceling, or toggling CI workflows has large side effects (CI minutes, deploy triggers, external webhooks). These commands are **not** listed in the user's global CLAUDE.md Tier 3 — `gh run rerun` actually sits in global `permissions.ask` (Tier 2) and the rest are unlisted — but the side-effect blast radius justifies a default-deny in this skill's project-local policy. Override to `ask` per-project if CI re-runs are routine.

### Cat 10 — gh api low-level: `gh api` low-level invocations (recommended: ask)

```
Bash(gh api:*)
```

`gh api` switches HTTP methods via flag combos (`-X DELETE`, `--method=DELETE`, auto-POST when `-f` is added, body via `--input file`) and flag order is flexible, so Bash permission arg-pattern matching cannot reliably isolate the method — see the official "Bash permission patterns that try to constrain command arguments are fragile" warning at `code.claude.com/docs/en/permissions`. A blanket `deny` would also block legitimate GET-only uses that only `gh api` can serve (PR review inline comments via `repos/{owner}/{repo}/pulls/{N}/comments`, custom properties, reaction breakdowns). Default `ask` with the expectation that the user eyeballs endpoint + method per invocation.

If `ask` becomes noisy, add **path-scoped allow rules** for the GET endpoints you hit often, e.g. `Bash(gh api repos/*/pulls/*/comments)`. Use plain glob `*`, **not** `{owner}` / `{repo}` literals — the permissions spec only defines `*` as a wildcard; curly-brace placeholders fall outside the spec and would be matched literally against argv like `octocat/Hello-World`.

### Cat 11 — Delete-class: Repository / Issue / Run / Cache / Secret / Variable deletions (recommended: deny)

```
Bash(gh repo delete:*)
Bash(gh issue delete:*)
Bash(gh run delete:*)
Bash(gh cache delete:*)
Bash(gh secret delete:*)
Bash(gh variable delete:*)
```

Repo / issue / secret / variable / Actions-cache deletion is irreversible from the GitHub side (no `gh` undo, no soft-delete state to restore from). The user's global CLAUDE.md already lists `gh repo delete *` and `gh issue delete *` in `permissions.deny`. This category bundles the rest of the delete-class verbs the skill knows about so that the policy is uniform: **all `gh ... delete` should require an explicit out-of-skill action by the user**. The default is `deny`. Release deletion (`gh release delete` / `gh release delete-asset`) lives in Cat 8 because it groups with the other release verbs.

### Cat 12 — git read-only: Read-only and branch-switch git ops (recommended: allow)

```
Bash(git status:*)        Bash(git diff:*)           Bash(git log:*)
Bash(git show:*)          Bash(git ls-files:*)       Bash(git ls-tree:*)
Bash(git rev-parse:*)     Bash(git blame:*)          Bash(git shortlog:*)
Bash(git remote:*)        Bash(git fetch:*)          Bash(git symbolic-ref:*)
Bash(git branch:*)        Bash(git switch:*)         Bash(git checkout:*)
Bash(git config --get:*)  Bash(git config --list:*)
```

These cover working-tree inspection, log queries, remote read, and branch switching. The `branch:*` / `checkout:*` patterns are deliberately broad — they also match destructive sub-uses like `git branch -D foo` and `git checkout -- file`, which are blocked by paired narrow deny entries in Cat 16 (`deny → ask → allow` first-match-wins per `code.claude.com/docs/en/permissions`). `git config --get` / `--list` are read-only; `git config` set (e.g. `git config user.email …`) is intentionally not allowed here because mis-set config silently affects every subsequent commit.

### Cat 13 — git local writes: Stage / commit / stash push (recommended: allow)

```
Bash(git add:*)           Bash(git commit:*)
Bash(git rm:*)            Bash(git mv:*)
Bash(git stash:*)
```

Staging, committing, file rename / removal (tracked), and stash push / pop are local-only and reversible (`git reset HEAD`, `git stash apply`). `git stash:*` deliberately covers `git stash drop` and `git stash clear` too — those *are* destructive (stashes cannot be recovered), and they are blocked by paired entries in Cat 16, mirroring the broad-allow + narrow-deny pattern from Cat 12.

### Cat 14 — git history rewrite: Merge / rebase / cherry-pick / revert / reset (recommended: ask)

```
Bash(git merge:*)         Bash(git rebase:*)
Bash(git cherry-pick:*)   Bash(git revert:*)
Bash(git reset:*)         Bash(git commit --amend:*)
```

These rewrite or merge history in ways that are non-trivial to undo (especially after a push). `git reset:*` covers `git reset --hard` too — the destructive form is downgraded to `deny` by a paired entry in Cat 16. Default `ask` lets the user eyeball the target ref before the rewrite.

### Cat 15 — git tag: Tag create / delete / push-prep (recommended: ask)

```
Bash(git tag:*)
```

Tag creation is local but typically followed by `git push --tags`, which would expose the tag publicly. Tag delete locally (`git tag -d X`) is reversible if you remember the SHA; tag delete on remote requires a separate push and is governed by Cat 17. Default `ask`.

### Cat 16 — git destructive local: Hard-reset / restore / checkout-overwrite / branch-D / clean / stash-drop (recommended: deny)

```
Bash(git reset --hard:*)         Bash(git restore:*)
Bash(git checkout --:*)          Bash(git checkout HEAD --:*)
Bash(git checkout origin/* --:*) Bash(git branch -D:*)
Bash(git clean -f:*)             Bash(git clean -fd:*)
Bash(git clean -fdx:*)
Bash(git stash drop:*)           Bash(git stash clear:*)
```

These overwrite uncommitted local work, force-delete branches with no merge check, drop stashes that cannot be recovered, or wipe untracked files. The user's global CLAUDE.md already lists every form in `permissions.deny` (`git reset --hard`, `git restore`, `git branch -D`, `git checkout -- *` family, etc.). This category mirrors them in the project-local policy and adds the `stash drop` / `clear` and `clean -f*` forms that the global policy notes as caveats. These entries are also what makes the broad allow in Cat 12 / 13 safe — the deny tier is checked first, so a `git branch -D` request hits this deny before reaching the Cat 12 allow.

### Cat 17 — git push: All forms of `git push` (recommended: deny)

```
Bash(git push:*)
```

A single broad pattern covers `git push`, `git push --force`, `git push origin <branch>`, `git push --tags`, `git push --delete`, etc. The user's global CLAUDE.md lists `git push *` as Tier 3 deny — pushed history is the moment local mistakes become public, so this category must not be auto-allowed by any project policy. Default `deny`. Override to `ask` only on a personal sandbox repo where the user accepts the friction of confirming each push.

## Step-by-step

### Step 1: Locate settings.local.json

```bash
git rev-parse --show-toplevel
```

The target is that path + `/.claude/settings.local.json`. Read the existing content with the `Read` tool. If the file does not exist, treat it as a fresh-write. If the working directory is not inside a git repository, `git rev-parse` will fail; in that case fall back to the current directory and inform the user.

### Step 2: Parse existing permissions

Read the three arrays `permissions.allow` / `permissions.ask` / `permissions.deny`. Entries already in those arrays are treated as "previously configured by the user" and preserved.

### Step 2.5: Show current state and offer an early exit

Before walking the user through 17 questions, summarize what is already present and let them opt out. This prevents the "answer 17 questions, get told nothing changed" experience.

Render the summary as concise text (not via AskUserQuestion, which is for choices, not for display):

- Total `gh ...` and `git ...` entries already in `permissions.allow` / `ask` / `deny`, with one or two example patterns each.
- A coverage hint: of the 17 categories, how many appear "already configured" (≥1 entry from that category present in any array) vs "untouched".

Then ask via AskUserQuestion (1 question):

- question: `Continue with the 17-category walkthrough, or exit now?`
- options:
  - `Continue (walk through all 17 categories)` (recommended when the user explicitly requested a setup pass)
  - `Exit (current settings look correct)` (recommended when the user only wanted to inspect what is there)

If `Exit` is chosen, report the summary and stop. If `Continue`, proceed to Step 3.

### Step 3: Ask the categories via AskUserQuestion batches

**Always use AskUserQuestion** (asking via plain text is prohibited). AskUserQuestion accepts **at most 4 questions per message**, so split the N categories into **⌈N/4⌉ batches**. For the current 17 categories that gives 5 batches of 4 + 4 + 4 + 4 + 1:

- **Batch 1** (4): Cat 1 Read-only / Cat 2 Local ops / Cat 3 Comments & reviews / Cat 4 Issue create/edit
- **Batch 2** (4): Cat 5 Issue close/reopen / Cat 6 PR create/edit / Cat 7 PR merge/close / Cat 8 Release ops
- **Batch 3** (4): Cat 9 Workflow execution / Cat 10 gh api low-level / Cat 11 Delete-class / Cat 12 git read-only
- **Batch 4** (4): Cat 13 git local writes / Cat 14 git history rewrite / Cat 15 git tag / Cat 16 git destructive local
- **Batch 5** (1): Cat 17 git push

If the category set grows (or shrinks) in a future version, re-derive the batches from the same `⌈N/4⌉` rule rather than maintaining a hard-coded list.

Each question takes this shape:

- **question**: `How should the commands in "<category-name>" be handled?` — keep the question body short. Do **not** inline the full command list in the question text; AskUserQuestion question / option strings have practical length limits and a 17-item list (e.g. Cat 1, Cat 12) breaks the UI.
- **header**: A short identifier for the category (max 12 chars, e.g. `Read-only`, `PR merge`, `gh api`, `Delete`, `git r-only`, `git push`, `git reset`).
- **multiSelect**: `false`
- **options**: 3 entries. **Put the recommended choice first and append `(recommended)` to its label.** Use each option's `description` field to carry a one-line summary of what the choice means **for this specific category**, including a 3–5 verb sample so the user is not selecting blind. Example for Cat 1 (Read-only):
  - label `Auto-allow (allow) (recommended)` — description: `Run gh view / list / status / diff / checks / search without a prompt. Safe — these are pure reads.`
  - label `Ask every time (ask)` — description: `Prompt before each read. Useful in audit-heavy contexts.`
  - label `Auto-deny (deny)` — description: `Block all gh read verbs in this project. Rare.`

For destructive categories (Cat 7 / 8 / 11 / 16 / 17), make the recommended `deny` option's description explicitly call out the irreversibility (e.g. `Block gh pr merge / close — these are effectively irreversible external writes`, `Block git push — pushed history is the moment local mistakes become public`, `Block git reset --hard / restore / branch -D / clean -fd — these overwrite uncommitted work with no undo`). The user must be able to tell apart a "safe allow" from a "Tier-3 deny" by reading the option, not by guessing from the category name.

For git categories that use the broad-allow + narrow-deny pattern (Cat 12 / 13 paired with Cat 16), the recommended `allow` option's description must note the safeguard so the user does not assume picking `allow` opens up `git branch -D` / `git stash drop`. Example for Cat 12: `Run git status / diff / log / branch / switch / checkout / fetch without a prompt. Destructive sub-forms (git branch -D, git checkout -- file) are blocked by Cat 16's deny entries when you accept that category's default.`

### Step 4: Route the answers into allow / ask / deny

For each category's selected choice, place every command pattern in that category as a candidate for the corresponding array. Union with the existing array and extract **only the new additions**.

**Pattern equivalence for dedupe.** The Claude Code permission docs treat trailing wildcards in two equivalent forms: `Bash(gh pr view *)` / `Bash(git status *)` (space + wildcard) and `Bash(gh pr view:*)` / `Bash(git status:*)` (colon-suffix wildcard). They match the same argv. The skill emits the colon form for new entries, but the user's existing entries (often inherited from `~/.claude/settings.json`, which uses the space form) may be in either notation. **Treat the two forms as the same pattern during dedupe**: when checking whether `Bash(git status:*)` is already present, also match `Bash(git status *)`. Without this, the skill double-adds entries on every run and `permissions.allow` grows redundantly. Use a simple normalization (e.g. replace the final `:*` with ` *` or vice versa before comparing) — the goal is "no semantically duplicate lines after writing", not full glob equivalence. This applies symmetrically to `gh ...` and `git ...` patterns.

### Step 5: Conflict check

If a new entry to be added already exists in a different array (e.g. trying to add to `allow` while it already sits in `deny`), it is a **conflict**.

For each conflict, ask via AskUserQuestion (singly or batched per message). **Prefix every conflict question with the same one-line disclaimer** so the user knows their answers are not applied until Step 6:

> `(Your answers here are collected and shown in a single preview at Step 6. Nothing is written to the file until you approve that preview.)`

This prefix is required — without it, users frequently assume each conflict answer commits immediately and either freeze on the prompt or pick "Keep existing" defensively.

- question: `"Bash(gh xxx:*)" / "Bash(git xxx:*)" is already in deny. Move it to allow?`
- options:
  - `Keep existing deny` (drop the new allow)
  - `Remove from deny and move to allow`
  - `Keep both` (in option `description`, briefly note that `code.claude.com/docs/en/permissions` defines evaluation order as **deny → ask → allow with deny always taking precedence**, so effective behavior stays "blocked"; this option is only useful as an audit trail. Keep the description under ~150 characters to stay within AskUserQuestion's practical option-description budget.)

When batching multiple conflicts into one AskUserQuestion call, order them by **(array name, then pattern string)** so the order is reproducible across runs.

If the user cancels mid-conflict-resolution (closes the AskUserQuestion or chooses an explicit cancel), abort the entire flow without writing — same policy as a mid-batch cancel in Step 3. Partial conflict resolution must not be persisted.

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

**Skip the prompt and exit early** when the **net change is zero**: zero additions across all three arrays AND zero removals from conflict resolution. Report "Everything is already configured (no additions, no removals)" and exit. If conflict resolution would remove entries even though additions are zero, the preview prompt is still required — removals count as changes the user must approve.

This preview prompt is the **explicit per-write confirmation required by the user's global CLAUDE.md Tier 2 rule for shared assets / `.claude/settings*.json`**. Even if the user pre-authorized the broader scope ("set up gh permissions for this project"), the Tier 2 rule treats `.claude/settings*.json` edits as requiring per-write confirmation, which this prompt satisfies.

If the user picks `Cancel`, exit without writing and report "Aborted; nothing was written. Re-run the skill to start over." Do not partially persist.

### Step 7: Write the file

**Decide which branch to take** by parsing the file read in Step 1:

- **Edit branch** — the file parsed cleanly AND `data.permissions` is present (even if its inner arrays are empty / missing).
- **Write branch** — the file did not exist (Step 1 fell back to "fresh-write"), OR the file existed but `data.permissions` is `undefined`.

**Edit branch:**

For each array (`allow`, `ask`, `deny`) that has new entries to add or has entries to remove (from Step 5 conflict resolution):

1. Read the current array literal from the file as it appears today (including its surrounding indentation and trailing comma if any).
2. Construct the new array literal by:
   - **Preserving the existing order** of entries that survive (no re-sorting; the user may have grouped related rules together).
   - **Appending new entries at the end** in the order they came out of Step 4.
   - **Removing only the entries flagged by Step 5 conflict resolution**.
3. Use `Edit` to replace the old array literal with the new one. Touch only the array members of `permissions.{allow,ask,deny}` — do not reformat other keys (`enabledPlugins`, etc.) and do not normalize unrelated whitespace. Non-`gh` / non-`git` entries inside `permissions.{allow,ask,deny}` (e.g. `Bash(npm test:*)`, `Read(.env*)`) must survive unchanged.

If a target array does not exist in the file (e.g. `permissions.ask` is missing entirely), insert it in the conventional order `allow → ask → deny` and only include it if it would be non-empty.

**Write branch** — use `Write` to create this minimal scaffolding:

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

**Both branches:**

- 2-space indent, trailing newline.
- If `.claude/` does not exist, run `mkdir -p <repo-root>/.claude` first — use the absolute path from Step 1's `git rev-parse --show-toplevel` (do **not** rely on `mkdir -p .claude` with a relative path; the shell cwd is not guaranteed to be the repo root by the time Step 7 runs).
- Before issuing the `Edit` / `Write`, **re-read the file** to detect concurrent edits since Step 1 (the user may have hand-edited it). If the content changed in a way that affects the additions / removals (existing entries flipped between arrays, the file became invalid JSON, etc.), abort and tell the user to re-run.

After writing, report the per-array additions (e.g. `allow +5, ask +3, deny +7`), any removals from conflict resolution, and the write path in 1–2 sentences and exit.

## Edge cases

- **Corrupted JSON**: If the `Read` content cannot be parsed (equivalent to `JSON.parse` failure), tell the user "Fix the JSON syntax error in `.claude/settings.local.json` first and re-run" and abort. Surface concrete recovery hints: (a) run `jq . .claude/settings.local.json` to see the parser's line-and-column pointer at the offending token, (b) if the file is tracked in git (rare for `*.local.json` but possible if `.gitignore` was misconfigured), `git diff` and `git restore` can revert to the last known-good state, (c) keep a backup with `cp .claude/settings.local.json .claude/settings.local.json.bak` before manual edits.
- **Patterns from the same category are scattered across multiple arrays**: treat as a conflict and resolve in Step 5.
- **Monorepo / not a git repository**: if `git rev-parse --show-toplevel` fails, fall back to the current directory and inform the user. Recommend they cd to the intended repository root and re-run, because writing `.claude/settings.local.json` at an arbitrary cwd can pollute a parent directory.
- **`.claude/` does not exist**: the `Write` tool does not auto-create parent directories, so run `mkdir -p <repo-root>/.claude` first using the absolute path from Step 1.
- **User cancels mid-batch (Step 3)**: do not proceed to Step 4 with only partially collected answers. Tell the user "Aborting. Nothing has been written." and exit.
- **User cancels mid-conflict-resolution (Step 5)** or **clicks Cancel in the preview (Step 6)**: same policy — exit without writing, no partial persistence.
- **Concurrent edit between Step 1 and Step 7**: if the file content changed between the initial read and the pre-write re-read, abort and tell the user to re-run. The skill cannot reconcile changes it did not observe.
- **Re-running the skill (idempotency)**: A second consecutive run with the same choices produces a no-op — every candidate entry is already present, so additions are zero and Step 6 short-circuits with "Everything is already configured". This is a guaranteed property of the dedupe logic in Step 4.
- **Non-`gh` / non-`git` entries in `permissions.{allow,ask,deny}`**: never delete or reorder them. The skill only adds `Bash(gh ...)` and `Bash(git ...)` entries and only removes entries it is moving between arrays as part of an explicit Step 5 conflict resolution.
- **User says "all ask is fine"**: do not skip the per-category questions. As a shortcut, you may offer "do you want a global all-deny / all-ask / all-allow option?" only if the user explicitly asks, and present it via AskUserQuestion before the category-by-category flow. The default remains the fine-grained per-category flow.

## Why this design

- **Fine-grained 3-choice**: A tier selector cannot express "allow most things but keep one slice on ask", so the skill directly asks for category × {allow,ask,deny}.
- **AskUserQuestion throughout**: The user's global CLAUDE.md requires every confirmation to go through AskUserQuestion.
- **Tier-3 categories default to deny**: gh PR merge / PR close / release ops / delete-class, and git push / destructive local (reset --hard / restore / branch -D / clean -fd / stash drop) fall under the user's global CLAUDE.md Tier 3 (destructive / irreversible external writes, or locally-destructive writes with no undo). The skill must not recommend auto-allow for these. Tier-2 categories that fire external notifications (issue close / comments / issue create) or rewrite shared history (git merge / rebase / cherry-pick / revert / reset --soft|--mixed / tag) default to `ask` so the user keeps a per-invocation veto. `gh api` defaults to `ask` because Bash argument-pattern matching cannot reliably isolate the HTTP method or destructiveness — see Cat 10.
- **Broad-allow + narrow-deny for git**: Cat 12 / 13 ship broad allow patterns (`Bash(git branch:*)`, `Bash(git stash:*)`) that also match destructive sub-uses; Cat 16 ships paired narrow deny patterns (`Bash(git branch -D:*)`, `Bash(git stash drop:*)`) that override them via the `deny → ask → allow` first-match-wins rule. This mirrors how the user's global `~/.claude/settings.json` already structures these commands, so adopting the project-local entries from this skill produces uniform behavior across global and project scope. Users who pick `allow` for Cat 12 / 13 but `ask`/`allow` for Cat 16 break this safeguard — surface this in the Cat 16 option descriptions.
- **Do not break existing state**: No duplicate writes, preserve ordering of existing entries, do not touch keys outside `permissions` and do not touch non-`gh` / non-`git` entries inside `permissions.{allow,ask,deny}` — otherwise the user can no longer trust the settings file as a whole.
- **Surface conflicts explicitly**: If `allow` and `deny` would both contain the same entry, do not silently drop one. Ask. The goal is to keep the settings file trustworthy.
- **Pure-prompt, no helper scripts**: The merge / dedupe / conflict-detection logic is small enough to keep in the SKILL body, and bundling a `scripts/merge_permissions.py` would force the user to trust an additional bundled artifact for a one-shot operation. The trade-off is that the LLM must execute the dedupe correctly each time; the Step 7 pre-write re-read and the Step 6 preview confirmation are the safeguards. If the operation grows (e.g. support for `~/.claude/settings.json`, multi-tool patterns, lockfile-style ordering rules), the right move would be to extract a script.

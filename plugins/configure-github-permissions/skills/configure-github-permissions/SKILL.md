---
name: configure-github-permissions
description: Interactively configure GitHub CLI (gh) permissions in the **project-local** `.claude/settings.local.json` (not the committed `.claude/settings.json`, not the user-global `~/.claude/settings.json`) by asking the user category-by-category which gh operation groups should be `allow` / `ask` / `deny`. Use when the user wants to set up gh permissions, reduce gh prompt frequency, allowlist GitHub commands, configure which gh operations are auto-allowed, blocked, or prompt-on-use, mentions "too many gh prompts", says "edit settings.local.json for gh" / "organize gh permissions" / "auto-approve gh", or mentions setting up gh allowlist / permission tier / per-category permissions for a project. Walks through 11 categories (read-only, local ops, comment, issue create/edit, issue close, pr create/edit, pr merge/close, release, workflow run, gh api, delete-class) via AskUserQuestion, then merges the resulting `Bash(gh ...)` entries into `permissions.{allow,ask,deny}` without duplication. Prefer this skill over `fewer-permission-prompts` when the user wants an upfront category-based gh setup rather than transcript-driven cleanup; prefer this over `update-config` when the target is specifically `gh`, not arbitrary commands.
---

# Configure GitHub Permissions

## Overview

A skill that configures `gh` command permissions in the project's `.claude/settings.local.json` at **per-category granularity**. It walks the user through 11 categories × 3 choices (`allow` / `ask` / `deny`) via AskUserQuestion and routes each answer into `permissions.allow` / `permissions.ask` / `permissions.deny`.

**Why category-grained?** To support real-world policies like *"auto-allow all read-only operations, but explicitly deny irreversible operations such as merge / release / delete."* A coarse tier-based selector cannot express this — choosing `allow` for the read tier would also force the same setting on the comment tier. This skill lets the user decide each category independently.

**Why `.claude/settings.local.json` and not `.claude/settings.json`?** The skill targets the **gitignored** local file so that per-developer `gh` permission tweaks do not leak into the team's committed policy. Teams that want a shared baseline should hand-edit `.claude/settings.json` after agreeing on it; this skill stays out of that file. The user-global `~/.claude/settings.json` is also out of scope — it represents cross-project defaults and should be edited deliberately by the user.

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

## When NOT to Use

- **The user's global `~/.claude/settings.json` already covers their `gh` usage** and project-local override is not needed. Running the skill in that case mostly produces 0-addition runs and pads `.claude/settings.local.json` with entries the global policy already handles. Tell the user to inspect `~/.claude/settings.json` first.
- **No `gh` prompts are firing in practice.** Pre-emptively populating 11 categories worth of allow/ask/deny for verbs the user never invokes creates dead config without value. Wait until the user is actually friction-bound.
- **The user wants a one-off tweak to a single verb** (e.g. "just allow `gh pr view`"). Hand-edit `.claude/settings.local.json` or use the `update-config` skill — running an 11-category wizard for one entry is disproportionate.
- **The user wants a team-shared policy** committed into `.claude/settings.json`. The skill is hard-fixed to the gitignored local file. Edit the committed file by hand after the team agrees.

## Default selection logic

The recommended default for each category is derived from four rules. The same logic should be used to decide the default of any new category added in the future.

1. **Pure-read, no side effects → `allow`.** Read-only verbs (`view` / `list` / `status` / `diff` / `checks` / `search`) and locally-scoped no-op verbs (`gh pr checkout` = local branch creation, `gh browse` = browser launch) cannot mutate remote state, so prompting on them is pure friction.
2. **External-visible but reversible → `ask`.** Verbs that produce subscriber-visible side effects (comments, reviews, issue create / close / reopen, PR create / edit / ready) can be edited or undone after the fact, so per-invocation user verification is the right balance between safety and friction.
3. **Effectively irreversible external write → `deny`.** Verbs the user's global CLAUDE.md treats as Tier 3 (PR merge, PR close, release create / edit / delete, repo delete, issue delete) must not be auto-allowed by any project policy. Side-effect-heavy verbs with large blast radius (workflow run / enable / disable / cancel, run rerun) follow the same rule even when not explicitly Tier 3 in global settings, because the override-to-`ask` cost is low.
4. **Argument-pattern matching is fragile → `ask`.** `gh api` switches HTTP methods via `-X` and data flags, and Bash permission patterns cannot reliably isolate the method. The skill cannot ship a path-scoped allowlist as a default, so the safe baseline is per-invocation prompt.

When a category sits between two rules (e.g. `gh issue close` is Tier 2 but fires external notifications), prefer the **less destructive** default (here: `ask`, not `deny`) and let the user override via this skill's per-category prompt or via their own CLAUDE.md.

## Categories

11 categories × 3 choices (allow / ask / deny). The commands and recommended defaults are below.

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

`gh issue close` does fire external notifications (subscribers, Slack integrations, GitHub Actions triggers), but the action itself is reversible via `gh issue reopen`, so it sits in the global CLAUDE.md **Tier 2** band (locally-destructive / new external creation) rather than Tier 3. The default is `ask` so that the user can eyeball the issue number and the timing before sending the close. Repositories with a stricter policy — for example, public-facing issue trackers where even a transient close ping is high-cost — can override this to `deny` via their CLAUDE.md or by re-running this skill and choosing `deny`. `reopen` is benign on its own, but pairing it with `close` keeps the operational policy simple.

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

`gh api` switches HTTP methods via the `-X` flag and data flags (`-f` / `-F` / `--input`), so Bash permission argument-pattern matching cannot reliably isolate the method or its destructiveness. The official Claude Code documentation (`code.claude.com/docs/en/permissions`) also states **"Bash permission patterns that try to constrain command arguments are fragile"**. Bypass paths are numerous: flag reordering (`gh api foo -X DELETE` ⇄ `gh api -X DELETE foo`), the `=` form `--method=DELETE`, automatic POST promotion when `-f` is added, body submission via `--input file`, etc.

That said, there are legitimate GET-only use cases that **only** `gh api` can cover. Representative examples:

- **PR review comments (inline comments on specific diff lines)**: `gh pr view` cannot fully retrieve them; `gh api repos/{owner}/{repo}/pulls/{N}/comments` is required.
- Specific metadata (custom properties, triage status, issue reaction breakdowns).

Therefore a blanket `deny` would stop everyday read tasks like PR review tracking and issue metadata retrieval. The default is **`ask`**, with the operational expectation that the user visually verifies the endpoint and method at invocation time.

If `ask` becomes noisy, the recommended approach is to add **path-scoped allow rules for specific GET endpoints** the user hits frequently (e.g. `Bash(gh api repos/*/pulls/*/comments)`). The skill cannot ship such rules as defaults; the user adds them manually. Note that the placeholder syntax must use plain glob `*`, not `{owner}` / `{repo}` literals — the official permissions docs at `code.claude.com/docs/en/permissions` only specify `*` as the wildcard; curly-brace placeholders are outside the spec, so they are matched as literal characters and never line up with real argv like `octocat/Hello-World`.

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

## Step-by-step

### Step 1: Locate settings.local.json

```bash
git rev-parse --show-toplevel
```

The target is that path + `/.claude/settings.local.json`. Read the existing content with the `Read` tool. If the file does not exist, treat it as a fresh-write. If the working directory is not inside a git repository, `git rev-parse` will fail; in that case fall back to the current directory and inform the user.

### Step 2: Parse existing permissions

Read the three arrays `permissions.allow` / `permissions.ask` / `permissions.deny`. Entries already in those arrays are treated as "previously configured by the user" and preserved.

### Step 2.5: Show current state and offer an early exit

Before walking the user through 11 questions, summarize what is already present and let them opt out. This prevents the "answer 11 questions, get told nothing changed" experience.

Render the summary as concise text (not via AskUserQuestion, which is for choices, not for display):

- Total `gh ...` entries already in `permissions.allow` / `ask` / `deny`, with one or two example patterns each.
- A coverage hint: of the 11 categories, how many appear "already configured" (≥1 entry from that category present in any array) vs "untouched".

Then ask via AskUserQuestion (1 question):

- question: `Continue with the 11-category walkthrough, or exit now?`
- options:
  - `Continue (walk through all 11 categories)` (recommended when the user explicitly requested a setup pass)
  - `Exit (current settings look correct)` (recommended when the user only wanted to inspect what is there)

If `Exit` is chosen, report the summary and stop. If `Continue`, proceed to Step 3.

### Step 3: Ask the categories via AskUserQuestion batches

**Always use AskUserQuestion** (asking via plain text is prohibited). AskUserQuestion accepts **at most 4 questions per message**, so split the N categories into **⌈N/4⌉ batches**. For the current 11 categories that gives 3 batches of 4 + 4 + 3:

- **Batch 1** (4): Cat 1 Read-only / Cat 2 Local ops / Cat 3 Comments & reviews / Cat 4 Issue create/edit
- **Batch 2** (4): Cat 5 Issue close/reopen / Cat 6 PR create/edit / Cat 7 PR merge/close / Cat 8 Release ops
- **Batch 3** (3): Cat 9 Workflow execution / Cat 10 gh api low-level / Cat 11 Delete-class

If the category set grows (or shrinks) in a future version, re-derive the batches from the same `⌈N/4⌉` rule rather than maintaining a hard-coded list.

Each question takes this shape:

- **question**: `How should the gh commands in "<category-name>" be handled?` — keep the question body short. Do **not** inline the full command list in the question text; AskUserQuestion question / option strings have practical length limits and a 19-item list (e.g. Cat 1) breaks the UI.
- **header**: A short identifier for the category (max 12 chars, e.g. `Read-only`, `PR merge`, `gh api`, `Delete`).
- **multiSelect**: `false`
- **options**: 3 entries. **Put the recommended choice first and append `(recommended)` to its label.** Use each option's `description` field to carry a one-line summary of what the choice means **for this specific category**, including a 3–5 verb sample so the user is not selecting blind. Example for Cat 1 (Read-only):
  - label `Auto-allow (allow) (recommended)` — description: `Run gh view / list / status / diff / checks / search without a prompt. Safe — these are pure reads.`
  - label `Ask every time (ask)` — description: `Prompt before each read. Useful in audit-heavy contexts.`
  - label `Auto-deny (deny)` — description: `Block all gh read verbs in this project. Rare.`

For destructive categories (Cat 7 / 8 / 11), make the recommended `deny` option's description explicitly call out the irreversibility (e.g. `Block gh pr merge / close — these are effectively irreversible external writes`). The user must be able to tell apart a "safe allow" from a "Tier-3 deny" by reading the option, not by guessing from the category name.

### Step 4: Route the answers into allow / ask / deny

For each category's selected choice, place every command pattern in that category as a candidate for the corresponding array. Union with the existing array and extract **only the new additions**.

**Pattern equivalence for dedupe.** The Claude Code permission docs treat trailing wildcards in two equivalent forms: `Bash(gh pr view *)` (space + wildcard) and `Bash(gh pr view:*)` (colon-prefixed wildcard). They match the same argv. The skill emits the colon form for new entries, but the user's existing entries (often inherited from `~/.claude/settings.json`, which uses the space form) may be in either notation. **Treat the two forms as the same pattern during dedupe**: when checking whether `Bash(gh pr view:*)` is already present, also match `Bash(gh pr view *)`. Without this, the skill double-adds entries on every run and `permissions.allow` grows redundantly. Use a simple normalization (e.g. replace the final `:*` with ` *` or vice versa before comparing) — the goal is "no semantically duplicate lines after writing", not full glob equivalence.

### Step 5: Conflict check

If a new entry to be added already exists in a different array (e.g. trying to add to `allow` while it already sits in `deny`), it is a **conflict**.

For each conflict, ask via AskUserQuestion (singly or batched per message). **Prefix every conflict question with the same one-line disclaimer** so the user knows their answers are not applied until Step 6:

> `(Your answers here are collected and shown in a single preview at Step 6. Nothing is written to the file until you approve that preview.)`

This prefix is required — without it, users frequently assume each conflict answer commits immediately and either freeze on the prompt or pick "Keep existing" defensively.

- question: `"Bash(gh xxx:*)" is already in deny. Move it to allow?`
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
3. Use `Edit` to replace the old array literal with the new one. Touch only the array members of `permissions.{allow,ask,deny}` — do not reformat other keys (`enabledPlugins`, etc.) and do not normalize unrelated whitespace. Non-`gh` entries inside `permissions.{allow,ask,deny}` (e.g. `Bash(npm test:*)`, `Read(.env*)`) must survive unchanged.

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
- **Non-`gh` entries in `permissions.{allow,ask,deny}`**: never delete or reorder them. The skill only adds `Bash(gh ...)` entries and only removes entries it is moving between arrays as part of an explicit Step 5 conflict resolution.
- **User says "all ask is fine"**: do not skip the per-category questions. As a shortcut, you may offer "do you want a global all-deny / all-ask / all-allow option?" only if the user explicitly asks, and present it via AskUserQuestion before the category-by-category flow. The default remains the fine-grained per-category flow.

## Why this design

- **Fine-grained 3-choice**: A tier selector cannot express "allow most things but keep one slice on ask", so the skill directly asks for category × {allow,ask,deny}.
- **AskUserQuestion throughout**: The user's global CLAUDE.md requires every confirmation to go through AskUserQuestion.
- **Tier-3 categories default to deny**: PR merge / PR close / release ops / delete-class fall under the user's global CLAUDE.md Tier 3 (destructive / irreversible external writes). The skill must not recommend auto-allow for these. Tier-2 categories that fire external notifications (issue close / comments / issue create) default to `ask` so the user keeps a per-invocation veto. `gh api` defaults to `ask` because Bash argument-pattern matching cannot reliably isolate the HTTP method or destructiveness — see Cat 10.
- **Do not break existing state**: No duplicate writes, preserve ordering of existing entries, do not touch keys outside `permissions` and do not touch non-`gh` entries inside `permissions.{allow,ask,deny}` — otherwise the user can no longer trust the settings file as a whole.
- **Surface conflicts explicitly**: If `allow` and `deny` would both contain the same entry, do not silently drop one. Ask. The goal is to keep the settings file trustworthy.
- **Pure-prompt, no helper scripts**: The merge / dedupe / conflict-detection logic is small enough to keep in the SKILL body, and bundling a `scripts/merge_permissions.py` would force the user to trust an additional bundled artifact for a one-shot operation. The trade-off is that the LLM must execute the dedupe correctly each time; the Step 7 pre-write re-read and the Step 6 preview confirmation are the safeguards. If the operation grows (e.g. support for `~/.claude/settings.json`, multi-tool patterns, lockfile-style ordering rules), the right move would be to extract a script.

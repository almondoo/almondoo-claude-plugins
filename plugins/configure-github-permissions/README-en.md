# configure-github-permissions

Interactively configures `gh` (GitHub CLI) **and `git`** command permissions for Claude Code at a **category × 3-way** (`allow` / `ask` / `deny`) granularity, and writes the result into the project's `.claude/settings.local.json`.

## Why

Coarse presets like "allow read-only, ask everything else" cannot express realistic policies — e.g., *"auto-allow read-only and PR creation, but always deny merge / release / workflow runs / `git push` / `git reset --hard` because they are irreversible writes."* This skill asks one question per category, routing each operation group independently into the appropriate bucket.

## How it works

It walks through 17 categories × 3 choices across 5 `AskUserQuestion` batches (4+4+4+4+1). Cat 1–11 cover `gh`; Cat 12–17 cover `git`:

| # | Category | Default |
|---|---|---|
| 1 | gh Read-only (`gh ... view/list/status/diff/checks/search`) | `allow` |
| 2 | gh Local operations (`gh pr checkout`, `gh browse`) | `allow` |
| 3 | gh Comments & reviews (`gh issue/pr comment`, `gh pr review`) | `ask` |
| 4 | gh Issue create / edit | `ask` |
| 5 | gh Issue close / reopen | `ask` |
| 6 | gh PR create / edit / ready | `ask` |
| 7 | gh PR merge / close | `deny` |
| 8 | gh Release operations (create / edit / upload / delete) | `deny` |
| 9 | gh Workflow execution (`workflow run`, `run rerun`, …) | `deny` |
| 10 | `gh api` low-level | `ask` |
| 11 | gh Delete-class (`gh repo/issue/run/cache/secret/variable delete`) | `deny` |
| 12 | git Read-only (`git status/diff/log/show/branch/switch/checkout/fetch/remote`) | `allow` |
| 13 | git Local writes (`git add/commit/rm/mv/stash`) | `allow` |
| 14 | git History rewrite (`git merge/rebase/cherry-pick/revert/reset/commit --amend`) | `ask` |
| 15 | git Tag (`git tag`) | `ask` |
| 16 | git Destructive local (`git reset --hard/restore/checkout --/branch -D/clean -fd/stash drop`) | `deny` |
| 17 | git Push (`git push *`) | `deny` |

Cat 12 / 13 use a **broad-allow + narrow-deny** pattern. For example, `Bash(git branch:*)` also matches `git branch -D foo`, but `Bash(git branch -D:*)` in Cat 16 fires first under the `deny → ask → allow` first-match-wins rule (official spec `code.claude.com/docs/en/permissions`), so destructive sub-uses stay blocked. Choosing `allow` for Cat 12 / 13 while moving Cat 16 off `deny` breaks this safeguard.

After collecting answers, the skill:

1. Reads the existing `permissions.{allow,ask,deny}` from `.claude/settings.local.json` (creates a minimal skeleton if the file does not exist).
2. Computes additions per array and **deduplicates** against existing entries.
3. Detects **cross-array conflicts** (e.g., adding to `allow` something already in `deny`) and asks how to resolve them.
4. Shows a final preview (write target path + new entries per array) and writes only after explicit confirmation.

It does not touch keys other than `permissions.{allow,ask,deny}` and preserves the existing ordering.

## Install

```
/plugin marketplace add almondoo/almondoo-claude-plugins
/plugin install configure-github-permissions@almondoo-claude-plugins
```

## Usage

Invoke explicitly via slash command:

```
/configure-github-permissions:configure-github-permissions
```

It also activates from natural language. The skill matches when the user asks *"configure gh permissions"* / *"configure git permissions"* / *"reduce gh / git prompts"* / *"allowlist GitHub / git commands"* / *"set up per-category permissions for this project"* / *"block git push for this repo"*, or mentions allowlist / permission tier / `gh` / `git` deny-rule setup.

The write target is **fixed to the project's `.claude/settings.local.json`**. The committed `.claude/settings.json` and the user-global `~/.claude/settings.json` are deliberately out of scope — team-wide gh / git policy must be hand-placed elsewhere.

## When project-local override is actually worth it

Even when your `~/.claude/settings.json` already encodes a sensible default gh / git policy, per-project overrides are sometimes the right move:

- **Public OSS repo**: global has `gh issue close` at `ask`, but subscriber-notification blast is high — tighten this one repo to `deny`. Same idea for `git push` — pin it tighter than global to reduce accidental push risk.
- **CI-heavy monorepo**: global denies `gh workflow run` by default; on an internal tooling repo, loosen it to `ask` so manual re-runs are possible. Some teams also relax `git merge` from `ask` to `allow` for the same repo.
- **Personal sandbox repo**: global denies `gh release create` / `git push`, but on a private experimentation repo you want `allow` to keep force-pushing freely.

Conversely, if your global config already covers your usage and per-project override is unnecessary, running this skill mostly produces 0-addition runs — see `When NOT to Use` in the SKILL body.

### Pattern notation (colon vs space)

This skill writes patterns in the `Bash(gh xxx:*)` colon form. Global settings typically use the `Bash(gh xxx *)` space form. Per Claude Code's permission spec, **both forms match the same argv** and are interchangeable. Mixing them inside one `settings.local.json` is harmless. If you want one consistent style for grep / diff readability, hand-align to match your existing file — the skill tolerates both and de-duplicates across notations.

## Before running

- **Want to keep your existing `.claude/settings.local.json`?** Back it up first: `cp .claude/settings.local.json .claude/settings.local.json.bak`. The skill itself is idempotent (a second run is a no-op), but Step 5 (conflict resolution) is the one place where an existing entry can be moved between arrays — and "moved" means "removed from the source array".
- **Don't re-run on broken JSON.** The skill detects a parse failure and aborts. Run `jq . .claude/settings.local.json` to pinpoint the syntax error first.

## Layout

```
configure-github-permissions/
├── .claude-plugin/
│   └── plugin.json
├── skills/
│   └── configure-github-permissions/
│       └── SKILL.md
└── README.md
```

The absence of `scripts/` / `references/` / `agents/` is deliberate. The merge / dedupe / conflict-detection logic is small enough to stay inside SKILL.md, and pulling it into a separate script would force users to trust an additional bundled artifact for a one-shot operation (see "Why this design" in SKILL.md). If we ever extend the skill to handle `~/.claude/settings.json` or multi-tool patterns, that's the right moment to factor a script out.

## Design notes

- **Destructive categories default to `deny`.** gh merge / release / workflow execution, and git `push` / `reset --hard` / `restore` / `branch -D` / `clean -fd` / `stash drop` qualify as irreversible writes under the user's global Tier-3 policy, so the skill must not auto-recommend `allow` for them.
- **`gh api` is `ask`, not `deny`.** A blanket `deny` would also block legitimate GET usage such as fetching PR review inline comments (`gh api repos/{o}/{r}/pulls/{n}/comments`). The skill keeps it at `ask` and notes that path-scoped `allow` rules can be added manually for frequently used endpoints. Note: leaving the catch-all `Bash(gh api:*)` in `ask` means a path-scoped `allow` you add later will be **shadowed** by the `ask` — under the `deny → ask → allow` first-match-wins rule, the `ask` entry fires first. To make path-scoped `allow` effective, you must either remove the catch-all `ask` or move it to `deny`. This skill keeps the safer `ask` catch-all by default.
- **git uses broad-allow + narrow-deny.** Cat 12 / 13 broad allow patterns also match destructive sub-uses, but Cat 16 narrow denies fire first under tier order. This mirrors how the user's global `~/.claude/settings.json` already structures these commands, so global and project policy stay aligned.
- **Conflicts are surfaced, never resolved silently.** When an addition candidate collides with an existing entry in another array, the skill always confirms before writing — to preserve the trustworthiness of the settings file.

## License

[Apache-2.0](../../LICENSE)

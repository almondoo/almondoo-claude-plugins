# configure-github-permissions

Interactively configures `gh` (GitHub CLI) permissions for Claude Code at a **category × 3-way** (`allow` / `ask` / `deny`) granularity, and writes the result into the project's `.claude/settings.local.json`.

## Why

Coarse presets like "allow read-only, ask everything else" cannot express realistic policies — e.g., *"auto-allow read-only and PR creation, but always deny merge / release / workflow runs because they are irreversible external writes."* This skill asks one question per category, routing each operation group independently into the appropriate bucket.

## How it works

It walks through 10 categories × 3 choices across 3 `AskUserQuestion` batches:

| # | Category | Default |
|---|---|---|
| 1 | Read-only (`gh ... view/list/status/diff/checks/search`) | `allow` |
| 2 | Local operations (`gh pr checkout`, `gh browse`) | `allow` |
| 3 | Comments & reviews (`gh issue/pr comment`, `gh pr review`) | `ask` |
| 4 | Issue create / edit | `ask` |
| 5 | Issue close / reopen | `deny` |
| 6 | PR create / edit / ready | `ask` |
| 7 | PR merge / close | `deny` |
| 8 | Release operations (create / edit / upload / delete) | `deny` |
| 9 | Workflow execution (`workflow run`, `run rerun`, …) | `deny` |
| 10 | `gh api` low-level | `ask` |

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

```
/configure-github-permissions:configure-github-permissions
```

The skill activates automatically when the user asks to *"configure gh permissions"* / *"reduce gh prompts"* / *"allowlist GitHub commands"* / *"set up per-category permissions for this project"*, or mentions allowlist / permission tier / `gh` deny-rule setup.

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

## Design notes

- **Destructive categories default to `deny`.** Merge / release / workflow execution / `gh api` qualify as irreversible external writes under the user's global Tier-3 policy, so the skill must not auto-recommend `allow` for them.
- **`gh api` is `ask`, not `deny`.** A blanket `deny` would also block legitimate GET usage such as fetching PR review inline comments (`gh api repos/{o}/{r}/pulls/{n}/comments`). The skill keeps it at `ask` and notes that path-scoped `allow` rules can be added manually for frequently used endpoints.
- **Conflicts are surfaced, never resolved silently.** When an addition candidate collides with an existing entry in another array, the skill always confirms before writing — to preserve the trustworthiness of the settings file.

## License

[Apache-2.0](../../LICENSE)

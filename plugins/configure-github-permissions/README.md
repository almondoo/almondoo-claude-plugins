# configure-github-permissions

Interactively configure `gh` (GitHub CLI) permissions for Claude Code at the
**per-category × 3-choice** (`allow` / `ask` / `deny`) granularity, writing the
result into the project's `.claude/settings.local.json`.

## Why

Coarse tier presets ("allow read-only, ask the rest") cannot express
realistic policies like *"auto-allow read-only and PR creation, but always
deny merge / release / workflow execution because they are irreversible
external writes."* This skill asks one question per category so each
operation group lands in the right bucket independently.

## How it works

10 categories × 3 choices, asked across 3 `AskUserQuestion` batches:

| # | Category | Default |
|---|---|---|
| 1 | Read-only (`gh ... view/list/status/diff/checks/search`) | `allow` |
| 2 | Local ops (`gh pr checkout`, `gh browse`) | `allow` |
| 3 | Comments & reviews (`gh issue/pr comment`, `gh pr review`) | `ask` |
| 4 | Issue create / edit | `ask` |
| 5 | Issue close / reopen | `deny` |
| 6 | PR create / edit / ready | `ask` |
| 7 | PR merge / close | `deny` |
| 8 | Release ops (create / edit / upload / delete) | `deny` |
| 9 | Workflow execution (`workflow run`, `run rerun`, …) | `deny` |
| 10 | `gh api` low-level | `ask` |

After collecting answers, the skill:

1. Reads existing `permissions.{allow,ask,deny}` in
   `.claude/settings.local.json` (creates the file with minimal scaffolding
   if absent).
2. Computes the additions per array, **dedupes** against existing entries.
3. Surfaces **cross-array conflicts** (e.g. trying to add to `allow` what
   already sits in `deny`) and asks how to resolve.
4. Shows a final preview (target path + per-array new entries) and writes
   only on explicit confirmation.

The skill never touches keys other than `permissions.{allow,ask,deny}` and
preserves existing ordering.

## Install

```
/plugin marketplace add almondoo/almondoo-claude-plugins
/plugin install configure-github-permissions@almondoo-claude-plugins
```

## Usage

```
/configure-github-permissions:configure-github-permissions
```

The skill also auto-activates when the user asks to *"set up `gh`
permissions"*, *"reduce gh prompt frequency"*, *"allowlist GitHub
commands"*, *"configure per-category permissions for this project"*, or
mentions setting up an allowlist / permission tier / `gh` deny rules.

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

- **Destructive categories default to `deny`.** Merge, release, workflow
  execution, and `gh api` are irreversible external writes per the user's
  global Tier-3 policy; the skill must not auto-recommend `allow` for
  them.
- **`gh api` is `ask`, not `deny`.** A blanket `deny` would block
  legitimate GET-only use cases (e.g. PR review inline comments via
  `gh api repos/{o}/{r}/pulls/{n}/comments`). The skill keeps it as
  `ask` and notes that path-scoped `allow` rules can be added manually
  for frequently-hit endpoints.
- **Conflicts are surfaced, not silently resolved.** If an addition
  collides with an existing entry in another array, the skill asks
  before writing — keeping the settings file trustworthy.

## License

[Apache-2.0](../../LICENSE)

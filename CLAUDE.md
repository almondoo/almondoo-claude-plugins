# CLAUDE.md

Claude Code plugin marketplace (`almondoo-claude-plugins`).

## Security check before code changes

Before editing or generating **any** code in this repository, briefly assess the security impact and surface the risk **before** writing the change. Even small edits ship to anyone who installs the plugin, so the time to think about safety is up-front, not after the diff exists. Triggers (apply this check whenever the change touches any of these):

- **Plugin scripts that execute under the user's shell** (`plugins/*/skills/*/scripts/*.{sh,py,js,ts}`): verify quoting, argument validation, no unguarded `eval` / `exec` / unquoted variable expansion, no command injection from `$ARGUMENTS` / user-supplied paths.
- **Spawn-prompt / SKILL.md placeholder interpolation**: a `<PLACEHOLDER>` substituted from user input or `gh` / `git` output can carry shell metacharacters or prompt-injection payloads downstream. Treat external strings as untrusted at the substitution boundary.
- **Authentication / authorization, secrets, PII, sensitive-data handling** — including log lines, error messages, and AskUserQuestion previews that might echo a token or key.
- **Injection / path-traversal vectors** when parsing external input into shell, JSON, SQL, HTML, regex, or template engines.
- **Dependency or distribution changes** (`plugin.json` / `marketplace.json` / runtime deps a script pulls): supply-chain risk; pin or pre-verify upstream.
- **Loosening an existing safety constraint** — relaxing a deny rule, broadening an allow-list, removing validation, or weakening a tier-2/tier-3 boundary from the user-level CLAUDE.md.
- **New external write paths** (network calls, filesystem writes outside `tmp/`, MCP / API mutations).

If a trigger applies, state the risk and its mitigation in one or two sentences before applying the edit. When the user has explicitly asked for a change that introduces a security risk, surface the risk so they can decide rather than silently accepting it.

## Layout

- Register every `plugins/<name>/skills/<name>/SKILL.md` in the root `.claude-plugin/marketplace.json`.
- The `name:` in each SKILL.md frontmatter must match the directory basename.
- Per-plugin design decisions, iteration history, and operational gotchas are accumulated in `docs/learnings/<name>.md` at the repo root — outside `plugins/` so installed plugins do not carry maintainer-side history.

### Runtime workspaces — never under `plugins/`

When a plugin needs a scratch directory at execution time (iteration logs, eval artifacts, `static.json` outputs, etc.), it MUST write under the project root's `tmp/` — e.g. `tmp/<plugin>-workspace/iteration-N/`. `tmp/` is already gitignored, so the artifacts stay out of the published plugin AND out of git history.

Do **not** write workspaces under `plugins/<name>/skills/` — past incident: `plugins/parallel-audit/skills/parallel-audit-workspace/` accumulated 72 files containing absolute `/Users/tm/...` paths that would have shipped via `/plugin install`. The earlier `**/skills/*-workspace/` gitignore line masked this in git status but did not stop `/plugin install` from distributing the directory.

Also do not write to OS `/tmp` — see the user-level CLAUDE.md `## Temporary Files` rule (sandbox isolation / mid-task cleanup risk).

## Version bump

- Run `./.claude/skills/bump-plugin-version/scripts/bump.sh <plugin> <semver>` to keep `marketplace.json` and `plugin.json` in sync.
- Known side effect: `jq` pretty-print expands the `keywords` array of `marketplace.json` into multi-line form. Accepted as-is.
- After any edit, validate JSON with `jq . <file>`.

## Language policy

**EVERY file inside `plugins/*/` is English-only. The ONLY exception is the README family.** This is not a default, not a guideline, and not negotiable: skills and plugins ship to an international audience, Anthropic's own skills are English-based, and a single Japanese sentence inside SKILL.md / `references/` / `agents/` / `prompts/` / `scripts/` / `plugin.json` makes the artifact incoherent for the people downloading it.

### Must be English (no Japanese permitted)

- `plugins/*/skills/*/SKILL.md` — including frontmatter.
- `plugins/*/skills/*/references/` — every file.
- `plugins/*/skills/*/agents/` and `prompts/` — every prompt template.
- `plugins/*/skills/*/scripts/` — code, comments, docstrings, log lines, CLI help text. The single allowed deviation is **localization data** for user-facing output (see the next section).
- `plugins/*/.claude-plugin/plugin.json` (`description` / `keywords`).
- Root `.claude-plugin/marketplace.json` (`description` / `keywords`).
- `CLAUDE.md` and `CLAUDE.local.md` (project rule files).
- Commit messages, PR titles, PR bodies.

If you find Japanese (or any non-English text) inside any of these targets, **translate it on the spot in the same change**. Do not leave mixed-language files behind. Do not add Japanese "for clarity" — write the clarification in English.

### README family — the one exception

Plugin READMEs are bilingual:

- `plugins/*/README.md` — Japanese. Canonical for plugin READMEs.
- `plugins/*/README-en.md` — English mirror.

Keep both in sync. When you edit one, update the other in the same change.

### `docs/learnings/` — internal log, Japanese permitted

`docs/learnings/<plugin>.md` at the repo root is the maintainer's internal session log: design decisions, iteration history, operational gotchas. **These files are intentionally Japanese** — they are written by and for almondoo, and they sit outside `plugins/` so they never ship with an installed plugin. The audience is the internal team, not downloaders.

Do not translate `docs/learnings/` to English. If you find English-only entries there, leave them; if you find a mixed file, prefer Japanese as the consolidating language.

### Localization data inside scripts

When a renderer / script intentionally produces user-facing output in multiple languages (a `LOCALES` dict carrying `ja` and `en` copies of UI labels, for example), the non-English strings are **output data**, not source content. They are allowed inside the otherwise English-only file.

The rule: surrounding code, comments, and identifiers stay English; only the literal string values in the language-keyed table may contain other languages. If a script grows enough localization data to feel like content rather than data, extract it into a separate `locales/` file rather than relaxing the rule.

Verifying the rule:

```bash
# any Japanese left in plugin source?
find plugins -type f \( -name "*.md" -o -name "*.json" -o -name "*.py" -o -name "*.sh" \) \
  | grep -v -E '(README\.md|README-en\.md)' \
  | xargs python3 -c "import sys; [print(p) for p in sys.argv[1:] if any('぀'<=c<='ヿ' or '一'<=c<='鿿' for c in open(p,encoding='utf-8').read())]"
```

(Exception: a `LOCALES["ja"]` localization data block is expected to match — see the localization-data exception above.)

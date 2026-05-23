# CLAUDE.md

Claude Code plugin marketplace (`almondoo-claude-plugins`).

## Layout

- Register every `plugins/<name>/skills/<name>/SKILL.md` in the root `.claude-plugin/marketplace.json`.
- The `name:` in each SKILL.md frontmatter must match the directory basename.
- Per-plugin design decisions, iteration history, and operational gotchas are accumulated in `docs/learnings/<name>.md` at the repo root — outside `plugins/` so installed plugins do not carry maintainer-side history.

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

When a renderer / script intentionally produces user-facing output in multiple languages (for example, the `LOCALES` dict in `plugins/skill-eval/skills/skill-eval-viewer/scripts/render_html.py` carries `ja` and `en` copies of report labels), the non-English strings are **output data**, not source content. They are allowed inside the otherwise English-only file.

The rule: surrounding code, comments, and identifiers stay English; only the literal string values in the language-keyed table may contain other languages. If a script grows enough localization data to feel like content rather than data, extract it into a separate `locales/` file rather than relaxing the rule.

### Workspaces (not part of the plugin)

`skill-eval` writes its evaluation artefacts to `tmp/skill-eval/<skill-name>/iteration-N/` under the project root — **never inside `plugins/`**, so installed plugins do not ship a per-target evaluation history. `tmp/` is gitignored at the marketplace root and by convention in user projects. The workspace's report.md / report.html language follows the user's prompt language; if you see one, do not "fix" its language.

Verifying the rule:

```bash
# any Japanese left in plugin source?
find plugins -type f \( -name "*.md" -o -name "*.json" -o -name "*.py" -o -name "*.sh" \) \
  | grep -v -E '(README\.md|README-en\.md)' \
  | xargs python3 -c "import sys; [print(p) for p in sys.argv[1:] if any('぀'<=c<='ヿ' or '一'<=c<='鿿' for c in open(p,encoding='utf-8').read())]"
```

(Exception: the renderer's `LOCALES["ja"]` localization data block is expected to match — see the localization-data exception above.)

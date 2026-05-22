# CLAUDE.md

Claude Code plugin marketplace (`almondoo-claude-plugins`)。

## Layout

- `plugins/<name>/skills/<name>/SKILL.md` を root `.claude-plugin/marketplace.json` に登録。
- SKILL.md frontmatter の `name:` は directory basename と一致させる。
- 個別 plugin の設計判断・iteration 履歴・運用 gotcha は `plugins/<name>/docs/LEARNINGS.md` に蓄積。

## Version bump

- `./.claude/skills/bump-plugin-version/scripts/bump.sh <plugin> <semver>` で `marketplace.json` と `plugin.json` を同期。
- 副作用: `jq` pretty-print が `marketplace.json` の `keywords` を multi-line 展開 (現状仕様として受容)。
- 編集後は必ず `jq . <file>` で JSON 妥当性確認。

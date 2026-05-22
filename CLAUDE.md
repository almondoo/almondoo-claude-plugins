# CLAUDE.md

Claude Code plugin marketplace (`almondoo-claude-plugins`)。

## Layout

- `plugins/<name>/skills/<name>/SKILL.md` を root `.claude-plugin/marketplace.json` に登録。
- SKILL.md frontmatter の `name:` は directory basename と一致させる。

## Version bump

- `./.claude/skills/bump-plugin-version/scripts/bump.sh <plugin> <semver>` で `marketplace.json` と `plugin.json` を同期。
- 副作用: `jq` pretty-print が `marketplace.json` の `keywords` を multi-line 展開 (現状仕様として受容)。
- 編集後は必ず `jq . <file>` で JSON 妥当性確認。

## Multi-agent audit プラグイン (`claude-md-parallel-audit` / `skill-md-parallel-audit`)

- N=9 iter 1 回 ≈ 440k tokens (Phase 2 ~290k + verifiers ~150k)。5-iter audit ≈ 1.5-2M tokens。
- **収束は asymptotic, not zero** — 修正サイクルが新 wording を生み HIGH avg が再上昇する。≥4/9 残存 findings は "known asymptote" として受容し、無限 iter は追求しない。
- Auditor subagent は global CLAUDE.md の "use Glob/Grep" 規約を継承しない (Bash `find`/`grep` を使うことがある)。気になる場合は dispatch prompt で明示。
- **Exclusion list の蓄積**: 過去 iter で FALSE 判定された finding (例: 公式 `subagent_type` を "undefined" flag、文書化済み override を矛盾と flag) を次 iter の exclusion に渡してノイズ抑制。

## Sibling engine sharing (smpa)

- `skill-md-parallel-audit` は `agents/{auditor,false-positive-detector,fix-safety-checker}.md` を `claude-md-parallel-audit` から **byte-for-byte copy**。`skill-md-redundancy-checker.md` のみ SKILL.md 固有。
- 共有 3 ファイルを更新する際は両 plugin に同時適用。
- Phase 構造差分: cmpa は Phase 6a/6b 分割 (auto-mode classifier playbook あり)、smpa は Phase 6 単体 + Phase 6.5 (post-fix `skill-eval` re-check)。

## Auto-mode classifier

- Plugin source の `plugins/*/skills/*/SKILL.md` → NOT protected (plugin artifact)。
- Installed `~/.claude/skills/*/SKILL.md` → protected (user CLAUDE.md Tier 2)。Edit 拒否時は `claude-md-parallel-audit` Phase 6b authorization template を使用。

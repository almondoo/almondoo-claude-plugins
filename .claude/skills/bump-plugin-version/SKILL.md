---
name: bump-plugin-version
description: Use when bumping a plugin's version in this marketplace — updates the entry in .claude-plugin/marketplace.json and plugins/<name>/.claude-plugin/plugin.json atomically so the two never drift
disable-model-invocation: true
---

# bump-plugin-version

`CLAUDE.local.md` の運用ルール「バージョンを上げる場合は `marketplace.json` のエントリと `plugin.json` の `version` を揃える」を機械化する。

## 使い方

ユーザーから `<plugin-name>` と `<new-version>` (semver, 例 `0.2.0`) を受け取って、次を実行する。

1. リポジトリルートで bump スクリプトを実行する:

   ```bash
   ./.claude/skills/bump-plugin-version/scripts/bump.sh <plugin-name> <new-version>
   ```

2. 生成された差分を `git diff -- .claude-plugin/marketplace.json plugins/<plugin-name>/.claude-plugin/plugin.json` で確認し、`<plugin-name>` の version が 2 箇所とも `<new-version>` に揃ったことを報告する。

3. 検証:
   - `jq -e --arg n "<plugin-name>" --arg v "<new-version>" '.plugins[] | select(.name == $n) | .version == $v' .claude-plugin/marketplace.json`
   - `jq -e --arg v "<new-version>" '.version == $v' plugins/<plugin-name>/.claude-plugin/plugin.json`
   - どちらも `true` を返すこと

## 引数

- `<plugin-name>` (必須): 既に `marketplace.json` に登録済みのプラグイン名
- `<new-version>` (必須): semver 形式 `MAJOR.MINOR.PATCH`

## 失敗時の挙動

- `<plugin-name>` が `marketplace.json` に存在しない → exit 1
- `plugins/<plugin-name>/.claude-plugin/plugin.json` が存在しない → exit 1
- `<new-version>` が semver に見えない → exit 1
- どの失敗ケースでもファイルは書き換えない

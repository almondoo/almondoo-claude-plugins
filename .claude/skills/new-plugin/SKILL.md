---
name: new-plugin
description: Use when adding a new plugin to this marketplace — scaffolds plugins/<name>/ with plugin.json, a starter SKILL.md, and README, then registers the entry in .claude-plugin/marketplace.json
disable-model-invocation: true
---

# new-plugin

このマーケットプレイス (`almondoo-claude-plugins`) に新しいプラグインを追加するときに使う。README に書かれている 3 ステップ (ディレクトリ作成 / `plugin.json` 作成 / `marketplace.json` 登録) を一括で行う。

## 使い方

ユーザーから `<plugin-name>` と任意で `<description>` を受け取って、次の順で実行する。プラグイン名は `kebab-case` (英小文字 + 数字 + ハイフンのみ) であることを確認する。

1. リポジトリルートで scaffold スクリプトを実行する:

   ```bash
   ./.claude/skills/new-plugin/scripts/scaffold.sh <plugin-name> "<description>"
   ```

2. 生成・更新されたファイルを `git status` で確認し、ユーザーに次を報告する:
   - 生成された `plugins/<plugin-name>/` 配下のファイル一覧
   - `.claude-plugin/marketplace.json` の差分 (新エントリ)

3. 検証 (`CLAUDE.local.md` の verification ルール):
   - `jq . .claude-plugin/marketplace.json` でルートの妥当性
   - `jq . plugins/<plugin-name>/.claude-plugin/plugin.json` で plugin manifest の妥当性
   - `plugins/<plugin-name>/skills/<plugin-name>/SKILL.md` の frontmatter `name` がディレクトリ名と一致していること

4. 次のアクションを提示:
   - SKILL.md の本文を実装する (現状はプレースホルダ)
   - `plugins/<plugin-name>/README.md` を編集する
   - 必要なら `marketplace.json` の `category` と `keywords` を埋める (現状はそれぞれ `productivity` と空配列)

## 引数

- `<plugin-name>` (必須): kebab-case の英小文字 + 数字 + ハイフン
- `<description>` (任意): `marketplace.json` と `plugin.json` 両方に書き込む 1〜2 文の説明。省略時はプレースホルダが入る

## 失敗時の挙動

- `plugins/<plugin-name>/` が既に存在する場合は scaffold スクリプトが exit 1 で停止する。上書きはしない
- `marketplace.json` のパースに失敗した場合は何も書き込まずに終了する

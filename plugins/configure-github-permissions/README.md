# configure-github-permissions

Claude Code 向けの `gh` (GitHub CLI) パーミッションを **カテゴリ別 × 3 択** (`allow` / `ask` / `deny`) の粒度で対話的に設定し、結果をプロジェクトの `.claude/settings.local.json` に書き込みます。

## なぜ必要か

「read-only は allow、それ以外は ask」のような粗いプリセットでは、現実的なポリシー —— たとえば *「read-only と PR 作成は自動許可、merge / release / workflow 実行は不可逆な外部書き込みなので常に拒否」* —— は表現できません。このスキルは 1 カテゴリ 1 質問で尋ね、各操作グループを独立して適切なバケットに振り分けます。

## 仕組み

10 カテゴリ × 3 択を、3 回の `AskUserQuestion` バッチに分けて確認します:

| # | カテゴリ | 既定値 |
|---|---|---|
| 1 | Read-only (`gh ... view/list/status/diff/checks/search`) | `allow` |
| 2 | ローカル操作 (`gh pr checkout`, `gh browse`) | `allow` |
| 3 | コメント・レビュー (`gh issue/pr comment`, `gh pr review`) | `ask` |
| 4 | Issue 作成・編集 | `ask` |
| 5 | Issue クローズ・リオープン | `deny` |
| 6 | PR 作成・編集・ready 化 | `ask` |
| 7 | PR マージ・クローズ | `deny` |
| 8 | Release 操作 (create / edit / upload / delete) | `deny` |
| 9 | Workflow 実行 (`workflow run`, `run rerun`, …) | `deny` |
| 10 | `gh api` 低レベル | `ask` |

回答を集めた後、スキルは以下を実行します:

1. `.claude/settings.local.json` の既存の `permissions.{allow,ask,deny}` を読み込む (ファイルが無ければ最小限の雛形で作成)。
2. 配列ごとの追加分を計算し、既存エントリと **重複排除** する。
3. **配列間の競合** (例: `deny` にあるものを `allow` に追加しようとする) を検出し、解決方法を確認する。
4. 最終プレビュー (書き込み先パス + 配列ごとの新規エントリ) を表示し、明示的な確認後にのみ書き込む。

`permissions.{allow,ask,deny}` 以外のキーには触れず、既存の並び順を保持します。

## インストール

```
/plugin marketplace add almondoo/almondoo-claude-plugins
/plugin install configure-github-permissions@almondoo-claude-plugins
```

## 使い方

```
/configure-github-permissions:configure-github-permissions
```

ユーザーが *「gh のパーミッションを設定したい」* / *「gh のプロンプト頻度を減らしたい」* / *「GitHub コマンドを allowlist 化したい」* / *「このプロジェクトのカテゴリ別パーミッションを設定したい」* と依頼したとき、または allowlist / permission tier / `gh` deny ルールのセットアップに言及したときにも、スキルが自動起動します。

## レイアウト

```
configure-github-permissions/
├── .claude-plugin/
│   └── plugin.json
├── skills/
│   └── configure-github-permissions/
│       └── SKILL.md
└── README.md
```

## 設計メモ

- **破壊的カテゴリは既定 `deny`。** Merge / release / workflow 実行 / `gh api` はユーザーのグローバル Tier-3 ポリシーで不可逆な外部書き込みに該当するため、スキルは `allow` を自動推奨してはならない。
- **`gh api` は `deny` ではなく `ask`。** 全面 `deny` にすると、PR レビューインラインコメント取得 (`gh api repos/{o}/{r}/pulls/{n}/comments`) のような正当な GET 用途まで塞いでしまう。スキルは `ask` のまま維持し、頻用エンドポイントについてはパススコープ付きの `allow` ルールを手動で追加できることを案内する。
- **競合は明示し、サイレントには解決しない。** 追加候補が別配列の既存エントリと衝突した場合、スキルは書き込み前に必ず確認を取る —— 設定ファイルの信頼性を保つため。

## ライセンス

[Apache-2.0](../../LICENSE)

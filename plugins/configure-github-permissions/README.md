# configure-github-permissions

Claude Code 向けの `gh` (GitHub CLI) パーミッションを **カテゴリ別 × 3 択** (`allow` / `ask` / `deny`) の粒度で対話的に設定し、結果をプロジェクトの `.claude/settings.local.json` に書き込みます。

## なぜ必要か

「read-only は allow、それ以外は ask」のような粗いプリセットでは、現実的なポリシー —— たとえば *「read-only と PR 作成は自動許可、merge / release / workflow 実行は不可逆な外部書き込みなので常に拒否」* —— は表現できません。このスキルは 1 カテゴリ 1 質問で尋ね、各操作グループを独立して適切なバケットに振り分けます。

## 仕組み

11 カテゴリ × 3 択を、3 回の `AskUserQuestion` バッチに分けて確認します:

| # | カテゴリ | 既定値 |
|---|---|---|
| 1 | Read-only (`gh ... view/list/status/diff/checks/search`) | `allow` |
| 2 | ローカル操作 (`gh pr checkout`, `gh browse`) | `allow` |
| 3 | コメント・レビュー (`gh issue/pr comment`, `gh pr review`) | `ask` |
| 4 | Issue 作成・編集 | `ask` |
| 5 | Issue クローズ・リオープン | `ask` |
| 6 | PR 作成・編集・ready 化 | `ask` |
| 7 | PR マージ・クローズ | `deny` |
| 8 | Release 操作 (create / edit / upload / delete) | `deny` |
| 9 | Workflow 実行 (`workflow run`, `run rerun`, …) | `deny` |
| 10 | `gh api` 低レベル | `ask` |
| 11 | Delete 系 (`gh repo/issue/run/cache/secret/variable delete`) | `deny` |

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

明示的に起動するには slash command を使います:

```
/configure-github-permissions:configure-github-permissions
```

自然言語でも自動起動します。「gh のパーミッションを設定したい」「gh のプロンプト頻度を減らしたい」「GitHub コマンドを allowlist 化したい」「このプロジェクトのカテゴリ別パーミッションを設定したい」のような依頼、あるいは allowlist / permission tier / `gh` deny ルールのセットアップに言及したときに、スキルがマッチします。

書き込み対象は **プロジェクトの `.claude/settings.local.json`** に固定です。コミット対象の `.claude/settings.json` や user-global の `~/.claude/settings.json` は触りません — チームに共有する gh ポリシーは別途手で配置してください。

## いつ project-local で override したくなるか

global の `~/.claude/settings.json` が大体の `gh` 運用ポリシーを持っていても、プロジェクト単位で上書きしたい現実的なケースがあります。たとえば:

- **OSS で公開している repo**: global では `gh issue close` が `ask` でも、購読者通知の影響が大きいので **この repo だけ `deny`** に締める。
- **CI が日常的に走る monorepo**: global では `gh workflow run` が `deny` (default) でも、内製ツール repo では **`ask` に緩めて手動再実行を許可**。
- **個人 sandbox repo**: global では `gh release create` が `deny` だが、自分しか使わない実験 repo では **`allow` まで開放**。

逆に「global で十分に整っていて、project ごとの override が要らない」場合は、このスキルを走らせる価値は薄い。`When NOT to Use` (SKILL 本体) を参照。

### パターン記法 (colon vs space) について

このスキルが書き出す `gh` パターンは `Bash(gh xxx:*)` の colon 形式です。global settings は `Bash(gh xxx *)` の space 形式が一般的ですが、Claude Code の公式仕様では **両者は同じ argv にマッチする等価形式** です。`settings.local.json` 内で colon と space が混ざっても動作上の差はありません。人間の grep / diff で見やすさを優先したい場合は、既存ファイルの記法に手で揃えてください。スキルは混在を許容し、dedupe も両形式を等価視します。

## 実行前の推奨

- **既存の `.claude/settings.local.json` を残しておきたい** なら、実行前に `cp .claude/settings.local.json .claude/settings.local.json.bak` でバックアップしておくと差し戻しが楽です。スキル自身は冪等で 2 回目の実行は no-op になりますが、Step 5 (競合解決) で別配列への移動を選んだ場合だけ既存エントリが削除されます。
- **JSON を壊した状態で再実行しない**: スキルは破損 JSON を検知すると abort します。`jq . .claude/settings.local.json` で構文エラー位置を特定してから再実行してください。

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

`scripts/` / `references/` / `agents/` を持たないのは意図的な選択です。merge / dedupe / conflict 検出は SKILL.md の手順に含めても LLM 実行で十分まわせる規模であり、別ファイルに切り出す利得が小さい — という判断 (詳細は SKILL.md の "Why this design" 節)。将来 `~/.claude/settings.json` サポートや multi-tool 拡張などに踏み込む段になったら、scripts 化を再検討します。

## 設計メモ

- **破壊的カテゴリは既定 `deny`。** Merge / release / workflow 実行 / `gh api` はユーザーのグローバル Tier-3 ポリシーで不可逆な外部書き込みに該当するため、スキルは `allow` を自動推奨してはならない。
- **`gh api` は `deny` ではなく `ask`。** 全面 `deny` にすると、PR レビューインラインコメント取得 (`gh api repos/{o}/{r}/pulls/{n}/comments`) のような正当な GET 用途まで塞いでしまう。スキルは `ask` のまま維持し、頻用エンドポイントについてはパススコープ付きの `allow` ルールを手動で追加できることを案内する。
- **競合は明示し、サイレントには解決しない。** 追加候補が別配列の既存エントリと衝突した場合、スキルは書き込み前に必ず確認を取る —— 設定ファイルの信頼性を保つため。

## ライセンス

[Apache-2.0](../../LICENSE)

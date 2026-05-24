# configure-github-permissions

Claude Code 向けの `gh` (GitHub CLI) および `git` コマンドのパーミッションを **カテゴリ別 × 3 択** (`allow` / `ask` / `deny`) の粒度で対話的に設定し、結果をプロジェクトの `.claude/settings.local.json` に書き込みます。

## なぜ必要か

「read-only は allow、それ以外は ask」のような粗いプリセットでは、現実的なポリシー —— たとえば *「read-only と PR 作成は自動許可、merge / release / workflow 実行 / `git push` / `git reset --hard` は不可逆なので常に拒否」* —— は表現できません。このスキルは 1 カテゴリ 1 質問で尋ね、各操作グループを独立して適切なバケットに振り分けます。

## 仕組み

17 カテゴリ × 3 択を、5 回の `AskUserQuestion` バッチ (4+4+4+4+1) に分けて確認します。Cat 1–11 は `gh`、Cat 12–17 は `git`:

| # | カテゴリ | 既定値 |
|---|---|---|
| 1 | gh Read-only (`gh ... view/list/status/diff/checks/search`) | `allow` |
| 2 | gh ローカル操作 (`gh pr checkout`, `gh browse`) | `allow` |
| 3 | gh コメント・レビュー (`gh issue/pr comment`, `gh pr review`) | `ask` |
| 4 | gh Issue 作成・編集 | `ask` |
| 5 | gh Issue クローズ・リオープン | `ask` |
| 6 | gh PR 作成・編集・ready 化 | `ask` |
| 7 | gh PR マージ・クローズ | `deny` |
| 8 | gh Release 操作 (create / edit / upload / delete) | `deny` |
| 9 | gh Workflow 実行 (`workflow run`, `run rerun`, …) | `deny` |
| 10 | `gh api` 低レベル | `ask` |
| 11 | gh Delete 系 (`gh repo/issue/run/cache/secret/variable delete`) | `deny` |
| 12 | git Read-only (`git status/diff/log/show/branch/switch/checkout/fetch/remote`) | `allow` |
| 13 | git ローカル書き込み (`git add/commit/rm/mv/stash`) | `allow` |
| 14 | git 履歴書き換え (`git merge/rebase/cherry-pick/revert/reset/commit --amend`) | `ask` |
| 15 | git tag (`git tag`) | `ask` |
| 16 | git 破壊的ローカル (`git reset --hard/restore/checkout --/branch -D/clean -fd/stash drop`) | `deny` |
| 17 | git push (`git push *`) | `deny` |

Cat 12 / 13 は **広い allow + 細かい deny** パターンを採用しています。たとえば `Bash(git branch:*)` は `git branch -D foo` にも match しますが、Cat 16 の `Bash(git branch -D:*)` が `deny → ask → allow` の first-match-wins ルール (公式仕様 `code.claude.com/docs/en/permissions`) で先に当たるため、破壊的サブ用途は安全に塞がれます。Cat 12 / 13 を allow にしつつ Cat 16 を ask / allow にすると、このセーフガードは壊れます。

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

自然言語でも自動起動します。「gh のパーミッションを設定したい」「git のパーミッションを設定したい」「gh / git のプロンプト頻度を減らしたい」「GitHub / git コマンドを allowlist 化したい」「このプロジェクトのカテゴリ別パーミッションを設定したい」「`git push` だけはこのリポジトリで止めたい」のような依頼、あるいは allowlist / permission tier / `gh` / `git` deny ルールのセットアップに言及したときに、スキルがマッチします。

書き込み対象は **プロジェクトの `.claude/settings.local.json`** に固定です。コミット対象の `.claude/settings.json` や user-global の `~/.claude/settings.json` は触りません — チームに共有する gh / git ポリシーは別途手で配置してください。

## いつ project-local で override したくなるか

global の `~/.claude/settings.json` が大体の `gh` / `git` 運用ポリシーを持っていても、プロジェクト単位で上書きしたい現実的なケースがあります。たとえば:

- **OSS で公開している repo**: global では `gh issue close` が `ask` でも、購読者通知の影響が大きいので **この repo だけ `deny`** に締める。同じく `git push` を **global より厳しく ask に固定** して、誤 push の事故率を下げる。
- **CI が日常的に走る monorepo**: global では `gh workflow run` が `deny` (default) でも、内製ツール repo では **`ask` に緩めて手動再実行を許可**。`git merge` も同 repo では **default `ask` → `allow`** に開放するチームがある。
- **個人 sandbox repo**: global では `gh release create` / `git push` が `deny` だが、自分しか使わない実験 repo では **`allow` まで開放**して force-push も自由に。

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

- **破壊的カテゴリは既定 `deny`。** gh の merge / release / workflow 実行、git の `push` / `reset --hard` / `restore` / `branch -D` / `clean -fd` / `stash drop` はユーザーのグローバル Tier-3 ポリシーで不可逆な書き込みに該当するため、スキルは `allow` を自動推奨してはならない。
- **`gh api` は `deny` ではなく `ask`。** 全面 `deny` にすると、PR レビューインラインコメント取得 (`gh api repos/{o}/{r}/pulls/{n}/comments`) のような正当な GET 用途まで塞いでしまう。スキルは `ask` のまま維持し、頻用エンドポイントについてはパススコープ付きの `allow` ルールを手動で追加できることを案内する。なお、catch-all の `Bash(gh api:*)` を `ask` に入れた状態で path-scoped `allow` を追加しても、`deny → ask → allow` の first-match-wins ルール上 `ask` が先に当たるため `allow` は実質的に効きません。`allow` を効かせるには catch-all を抜くか deny に置き換える必要があります (このスキルは catch-all を `ask` に置く保守的構成を選択)。
- **git は「広い allow + 細かい deny」。** Cat 12 / 13 の broad allow は `git branch -D` のような破壊的サブ用途も match しますが、Cat 16 の narrow deny が `deny → ask → allow` の tier 順で先に当たるためブロックされます。これはユーザーの global `~/.claude/settings.json` で既に取られている構造をそのまま project-local に持ち込む形であり、global と project で挙動を揃えるのが狙い。
- **競合は明示し、サイレントには解決しない。** 追加候補が別配列の既存エントリと衝突した場合、スキルは書き込み前に必ず確認を取る —— 設定ファイルの信頼性を保つため。

## ライセンス

[Apache-2.0](../../LICENSE)

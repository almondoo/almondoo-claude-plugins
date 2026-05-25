# agent-teams

複数タスクを **Wave (波)** に分けて並列実装するためのチーム編成スキル。Lead + Implementer + Reviewer + Tester (+ 大規模/セキュリティ重大時は Security Checker 専任) を Phase 2 で一括 spawn し、コードレビュー / セキュリティチェック / テスト全件 regression を **品質ゲート** として工程に組み込んでいます。

## なぜ必要か

Implementer だけを並列に並べる素朴な並列実装は、レビュー・セキュリティチェック・テストが抜け落ちて品質が落ちます。さらに、複数 teammate が同じ working tree で `git add` / `git commit` を同時実行すると、他人の untracked / staged ファイルを巻き込んだ汚染コミットが発生します（過去事例あり）。

このスキルはその両方を構造的に防ぎます。

- **品質ゲート**: 1 task = 1 commit、コミットごとにレビュー、Wave 終端で 1 回だけ Tester 全件 regression。
- **Lead 集中 git 制御**: 破壊的 git は Lead だけ、しかも `git add` (per-path) と `git commit` (`--amend` 禁止) のみ。それ以外の破壊的 git (`reset` / `restore` / `push` / `rebase` / `merge` / `revert` / `--amend` / `branch -D` / `clean` / `stash drop` / `worktree remove` …) は **Lead でも禁止**。

## チーム構成

タスク規模で人数を決めます。

| 規模 | 人数 | 構成 |
|------|------|------|
| Small (1-2 files) | 2 | Lead + Implementer×1 + Reviewer×1 (security / test 兼任) |
| Medium (3-5 files) | 3-4 | Lead + Implementer×1-2 + Reviewer×1 (security 兼任) + Tester×1 |
| Large (6+ files) または security-critical | 5-6 | Lead + Implementer×2-3 + Reviewer×1 + Security Checker×1 (専任) + Tester×1 |

**Security upgrade**: 認証/認可、決済、PII / 機密データ、新規 API エンドポイント、ファイルアップロードなどに該当するタスクは 1 段階上の規模で扱う（2 ファイル変更でも JWT 実装なら Medium 扱い）。

## Wave 構造

典型は **「4 並列 + 2 blocked_by」の合計 6 タスク**。

```
Wave 1 (並列 4 タスク): impl-doc1 / impl-doc2 / impl-api1 / impl-api2
Wave 2 (Wave 1 完了に blocked_by): 2 タスク (impl-ai1 / impl-ui1、または Wave 1 完了 Implementer の再割当て)
```

タスク命名規約は `W<n>-<D|A|AI|UI><id>` (D=doc, A=api, AI=ai, UI=ui)、Implementer ハンドル命名規約は `impl-<area><N>`。

## ファイル所有権

**1 file = 1 owner**。タスク分割はファイル境界で行い、複数 teammate に同一ファイルを編集させません。共有ファイル変更は単一 teammate に集約するか、Wave を分けて直列化します。

## ワークフロー

1. **Phase 1 (計画)**: Lead が issue / spec / git log を読んで 6 タスクを選定 → Wave 構造を決定 → ユーザー承認。
2. **Phase 2 (一括 spawn)**: `TeamCreate` → `TaskCreate` → Implementer + Reviewer + Tester (+ Security Checker) を **一度の message で同時 spawn**。Reviewer / Tester は spawn 時点では待機。
3. **Phase 3 (実行)**: Implementer が実装 → ローカル検証 → Lead に commit 依頼 → Lead が `git add <path>` + `git commit` を代行 → Reviewer に依頼 → Critical/Important があれば Implementer に修正依頼。**最大 3 回の修正サイクルで収束しない場合は Lead が停止してユーザーにエスカレート**。
4. **Phase 4 (解散)**: 全 Reviewer PASS 後に Tester に 1 回だけ最終 regression → 全員 `shutdown_request` → `TeamDelete`。

## なぜ Tester は Wave 終端 1 回だけか

過去 Wave で Tester に commit 毎に検証依頼を出したところ、後半で context 圧で応答しなくなる事故が発生しました。Implementer の self-verification と Reviewer の review でコミット単位の品質は既に担保されているため、Tester は **Wave 終端で 1 回** のみ呼び、累積後の整合性確認に専念させます。

## 提供されるテンプレート

| ファイル | 用途 |
|---------|-----|
| `assets/spawn-prompts/implementer.md` | Implementer spawn prompt の雛形 |
| `assets/spawn-prompts/reviewer.md` | Reviewer spawn prompt の雛形 (OWASP Top 10 観点込み) |
| `assets/spawn-prompts/security-checker.md` | Security Checker 専任版 spawn prompt の雛形 |
| `assets/spawn-prompts/tester.md` | Tester spawn prompt の雛形 (軽量出力形式指定) |
| `assets/wave-template.md` | Wave 構成パターン (命名規約 / オーナー分離 / 完了条件) |
| `assets/lead-checklist.md` | Lead のフェーズ別チェックリスト |
| `references/git-permissions.md` | 全 git 操作の Lead 可否表 + Implementer ワークフロー |
| `references/implementer-pitfalls.md` | リテラル制御バイト等の頻発落とし穴 |
| `references/tester-optimization.md` | Tester 依頼集約原則 + Lead 直接検証ルート |

## 前提条件

このスキルは Claude Code の **Agent Teams** ランタイム (`TeamCreate` / `TaskCreate` / `TaskUpdate` / `TaskList` / `TaskGet` / `SendMessage` / `TeamDelete` といった deferred tool 群) に依存します。利用前に以下を確認してください。

- Claude Code **CLI** で起動していること（VSCode 拡張ではタスク管理ツールが過去に無効化されていた経緯があるため、本スキルは CLI 経由を推奨）
- Agent Teams 機能が有効な比較的新しいバージョンであること
- 環境によっては experimental flag (例: `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`) で gating されている場合があるため、ご利用バージョンの公式 docs を確認してください

Step 0 の `ToolSearch` が 7 個のスキーマを全部返さない場合は、Lead は `AskUserQuestion` でユーザに報告し、`Agent` ツールへのフォールバックは行いません（フォールバックすると Lead 集中 git 制御や品質ゲートが構造的に崩壊するため）。

## インストール

```
/plugin marketplace add almondoo/almondoo-claude-plugins
/plugin install agent-teams@almondoo-claude-plugins
```

## 使い方

自動発火は **無効化**（`disable-model-invocation: true`）されており、明示的に呼び出します。

```
/agent-teams work through issue 123
/agent-teams implement auth feature
/agent-teams add several helpers in parallel
```

引数が曖昧な場合は `AskUserQuestion` で確認してから Phase 1 に入ります（推測 spawn は禁止）。

### Step 0: 必須の `ToolSearch`

このスキルが使う `TeamCreate` / `TaskCreate` / `SendMessage` / `TaskUpdate` / `TeamDelete` などは **deferred tool** で、session 開始時点で schema が読み込まれていません。skill 起動直後に必ず `ToolSearch` で一括ロードします。これを省略すると `Agent` ツールへサイレントフォールバックしてしまい、Lead 集中 git 制御や品質ゲートが崩壊します。

## License

Apache-2.0

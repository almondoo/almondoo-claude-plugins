# parallel-audit

エージェント指示 markdown ファイル (CLAUDE.md / CLAUDE.local.md / AGENTS.md / GEMINI.md / SKILL.md) を **複数エージェントで並列に監査** し、**HIGH 重大度** の品質問題を洗い出します。検出対象は、修飾語の欠落・文法ミス・用語ゆれ・セクション間の論理矛盾・暗黙の前提・列挙漏れ・未定義語など。

## 位置付け

**日常的な保守用ではなく、特定の症状が出たときに使う diagnostic tool** として設計しています。想定する起動タイミング:

- 大規模な refactor / rule 追加直後の検証
- 特定 rule が無視されている / 誤適用されていると気付いたとき
- agent 挙動が drift したと感じたとき
- Claude model upgrade 後の挙動変化の切り分け

ルーチン用途は明示的に推奨しません (コスト不釣り合い + 残存 finding が asymptote 化するため)。Phase 1 でルーチン選択時には警告を出して続行確認します。

## 何をどの順番で行うか

収束するか `max_iterations` (既定 `3`) に達するまで以下を反復:

1. **Phase 1**: 症状ヒアリング (`AskUserQuestion`) → routine 選択時は警告 + 続行確認
2. **Phase 1.5**: scope narrowing (full file / section / rule-and-neighbors) で監査範囲を絞る
3. **Phase 2**: target_file / `N` / `threshold` / `max_iterations` / exclusion list を収集 (既定 `N=3` / `threshold=2` / `max_iterations=3`)。`target_type` (claude-md | skill-md) は path から自動判定
4. **Phase 2.5**: SKILL.md 対象かつ `skill-eval` 利用可なら静的 pre-check を実行
5. **Phase 3**: 各セクションの 1 行目的を draft → batch confirm (`fix-safety-checker` の intent baseline)
6. **Phase 4**: N 並列 `auditor` を `model: "sonnet"` で同一 turn dispatch
7. **Phase 5**: per-instance HIGH count + convergent issues (≥ threshold) の 2 表を生成
8. **Phase 6 / 6.5 / 7**: triage → `false-positive-detector` (REAL / FALSE / NEEDS_HUMAN) → `redundancy-checker` (target_type 分岐: Claude Code defaults または sibling skills, KEEP / SIMPLIFY / REMOVE)
9. **Phase 8 / 9 / 10**: fix draft (single / multi-option) → `fix-safety-checker` (SAFE / NEEDS_REVIEW / UNSAFE) → `AskUserQuestion` で 1 件ずつ承認
10. **Phase 11**: `Edit` で適用。CLAUDE.md / CLAUDE.local.md / `~/.claude/skills/*` など auto-mode classifier の trigger list に乗る target は Edit の **前に** 明示認可を取得 (pre-authorize)。trigger list 外の target は直接 Edit、ブロック時のみ playbook で reactive リトライ
11. **Phase 11.5**: post-fix 検証 ─ (a) audit 再 dispatch / (b) optional A/B benchmark (`references/ab-testing.md`) / (c) SKILL.md 対象なら `skill-eval` 静的再 run
12. **Phase 12**: 収束判定 (全 N が clean / `(N − threshold + 1)` 以上が clean / HIGH 平均プラトー / `max_iterations` / fix candidate 0)

## インストール

```
/plugin marketplace add almondoo/almondoo-claude-plugins
/plugin install parallel-audit@almondoo-claude-plugins
```

## 使い方

```
/parallel-audit:parallel-audit
```

ユーザーが指示ファイル (CLAUDE.md / SKILL.md など) について **監査 / レビュー / 検証 / 品質チェック** を依頼したとき、または *multi-agent audit* / *convergence audit* / *parallel review* / *instruction file consistency* / *audit my SKILL.md* といったキーワードに言及したとき、長い指示ファイルの欠陥に対して高い信頼性のある再現性を求めるときに、スキルが自動起動 **することを意図しています** (下記の Known limitations を参照)。

## Known limitations

- **In-session triggering recall は未検証**: skill-creator の `claude -p` backend では recall=0% (4 件の should-trigger eval で 0/4 hit)。実 Claude Code session での triggering は別経路だが、in-session の recall は未計測。確実に発火させたいときは `/parallel-audit:parallel-audit` で明示起動してください。
- **Should-trigger eval は trace review 止まり**: AskUserQuestion が subagent をブロックするため、肯定ケース (eval id 1-4) は end-to-end ベンチマーク未実施。否定ケース (eval id 5-7) のみ end-to-end 検証済み。
- **Phase 9 fan-out cost**: 不具合の多いファイル (fix candidate 5+ × multi-option) では cost-tier table の "+20-80k" を 4-9× 超える可能性 (SKILL.md "Known limitations" 参照)。
- **外部 target 運用サンプル数 = 1** (`~/.claude/CLAUDE.md`)。それ以外の CLAUDE.md / SKILL.md に対する挙動は未確認。

## レイアウト

```
parallel-audit/
├── .claude-plugin/
│   └── plugin.json
├── skills/
│   └── parallel-audit/
│       ├── SKILL.md                       # メインのスキル定義
│       ├── agents/
│       │   ├── auditor.md                 # 7 軸 HIGH 重大度監査 (file-type agnostic)
│       │   ├── false-positive-detector.md
│       │   ├── fix-safety-checker.md
│       │   └── redundancy-checker.md      # target_type 分岐 (defaults vs siblings)
│       ├── references/
│       │   ├── claude-md-specifics.md          # CLAUDE.md 固有 exclusion + auto-mode classifier playbook
│       │   ├── skill-md-specifics.md           # SKILL.md 固有 exclusion + skill-eval 連携
│       │   ├── shared-blind-spots.md           # target-type 非依存の共通 FP パターン (両 specifics から参照)
│       │   ├── ab-testing.md                   # Phase 11.5(b) optional A/B 統合ガイド
│       │   ├── pitfalls.md                     # workflow / aggregation / fix-proposal / target-specific の落とし穴集約
│       │   └── symptom-interview-protocol.md   # Phase 1 の症状構造化プロトコル
│       └── evals/
│           └── evals.json                 # トリガー / 振る舞いテスト
└── README.md
```

## 既存 2 plugin との関係

このスキルは `claude-md-parallel-audit` (v0.2.1) と `skill-md-parallel-audit` (v0.2.1) を統合した後継です。両 plugin は数 release 後に marketplace から削除予定。既存ユーザーは `parallel-audit` に移行してください。

主な変更点:

- 2 plugin の統合 (`target_type: claude-md | skill-md` で挙動分岐)
- default `N` を `9` → `3` に縮小 (event-driven positioning に合わせて、deep audit は opt-in)
- Phase 1 symptom triage + scope narrowing を新設 (full file 走査の前に対象を絞る)
- Phase 11.5 post-fix verify を標準化 (audit 再 dispatch + optional A/B)
- `max_iterations` default `5` → `3` (asymptote 認識を反映)

## テンプレート比較型監査との違い

このスキルは **独立した並列監査 + 再現性しきい値** に特化しており、テンプレートマッチングは行いません。公式マーケットプレイスの `claude-md-management:claude-md-improver` のようなテンプレート比較型監査とは置き換えではなく **補完関係** です。

## ライセンス

[Apache-2.0](../../LICENSE)

# claude-md-parallel-audit

CLAUDE.md (および `CLAUDE.local.md` / `AGENTS.md` / `GEMINI.md` などの同種のエージェント指示ファイル) を **複数エージェントで並列に監査** し、**HIGH 重大度** の品質問題を洗い出します。検出対象は、修飾語の欠落・文法ミス・用語ゆれ・セクション間の論理矛盾・暗黙の前提・列挙漏れ・未定義語など。

## 何をどの順番で行うか

収束するか `max_iterations` (既定 `5`) に達するまで以下を反復:

1. **Phase 1**: 対象ファイルパス / `N` / `threshold` / `max_iterations` / 除外リストを `AskUserQuestion` で収集 (既定 `N=9` / `threshold=4` / `max_iterations=5`)
2. **Phase 1.5**: 各セクションの 1 行目的を draft → batch confirm (`fix-safety-checker` の intent baseline)
3. **Phase 2**: N 並列 `auditor` を `model: "sonnet"` で同一 turn dispatch (HIGH 重大度を最大 10 件/instance)
4. **Phase 3**: per-instance HIGH count + convergent issues (≥ threshold) の 2 表を生成
5. **Phase 4 / 4.5 / 4.6**: triage → `false-positive-detector` (REAL / FALSE / NEEDS_HUMAN) → `default-redundancy-checker` (Claude Code default と被るか、KEEP / SIMPLIFY / REMOVE)
6. **Phase 5 / 5.5 / 5.6**: fix draft (single / multi-option) → `fix-safety-checker` (SAFE / NEEDS_REVIEW / UNSAFE) → `AskUserQuestion` で 1 件ずつ承認
7. **Phase 6**: `Edit` で適用 (エージェント設定ファイルが auto-mode classifier に拒否されたら明示認可を得て単発リトライ)
8. **Phase 7 / 8**: Phase 2 から再ディスパッチ → 収束判定 (全 N が clean / `(N − threshold + 1)` 以上が clean / HIGH 平均プラトー / max_iter / fix candidate 0)

## インストール

```
/plugin marketplace add almondoo/almondoo-claude-plugins
/plugin install claude-md-parallel-audit@almondoo-claude-plugins
```

## 使い方

```
/claude-md-parallel-audit:claude-md-parallel-audit
```

ユーザーが CLAUDE.md などの指示ファイルについて **監査 / レビュー / 検証 / 品質チェック** を依頼したとき、または *multi-agent audit* / *convergence audit* / *parallel review* / *instruction file consistency* といったキーワードに言及したとき、長い指示ファイルの欠陥に対して高い信頼性のある再現性を求めるときに、スキルが自動起動します。

## レイアウト

```
claude-md-parallel-audit/
├── .claude-plugin/
│   └── plugin.json
├── skills/
│   └── claude-md-parallel-audit/
│       ├── SKILL.md                       # メインのスキル定義
│       ├── agents/                        # 専門サブエージェント
│       │   ├── auditor.md
│       │   ├── default-redundancy-checker.md
│       │   ├── false-positive-detector.md
│       │   └── fix-safety-checker.md
│       └── evals/
│           └── evals.json                 # トリガー / 振る舞いテスト
└── README.md
```

## テンプレート比較型監査との違い

このスキルは **独立した並列監査 + 再現性しきい値** に特化しており、テンプレートマッチングは行いません。公式マーケットプレイスの `claude-md-management:claude-md-improver` のようなテンプレート比較型監査とは置き換えではなく **補完関係** です。

## ライセンス

[Apache-2.0](../../LICENSE)

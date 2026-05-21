# claude-md-parallel-audit

CLAUDE.md (および `CLAUDE.local.md` / `AGENTS.md` / `GEMINI.md` などの同種のエージェント指示ファイル) を **複数エージェントで並列に監査** し、**HIGH 重大度** の品質問題を洗い出します。検出対象は、修飾語の欠落・文法ミス・用語ゆれ・セクション間の論理矛盾・暗黙の前提・列挙漏れ・未定義語など。

## 仕組み

1. 同じファイルに対して **N 個の独立したサブエージェント** (既定 `N=9`) を投入して監査する。
2. **再現性** で findings を集約 — **N のうち K 個以上** (既定 `K=4`) で報告された問題のみを真のシグナルとして採用する。単発の検出はノイズとして破棄。
3. 結果を以下にトリアージする:
   - **修正可能な新規欠陥** — `AskUserQuestion` で具体的な修正案を提示。
   - **ユーザーが既に許容している構造的トレードオフ** — 別枠で列挙。
4. 収束 (K 回以上再現する HIGH 重大度の新規問題が出なくなる) まで反復、上限は `max_iter` ラウンド。

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

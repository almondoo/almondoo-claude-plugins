# skill-md-parallel-audit

SKILL.md (Claude Code プラグインの skill 仕様ファイル) を **複数エージェントで並列に監査** し、**HIGH 重大度** の品質問題を洗い出します。検出対象は、修飾語の欠落・文法ミス・用語ゆれ・セクション間の論理矛盾・暗黙の前提・列挙漏れ・未定義語など。`claude-md-parallel-audit` の **sibling** で、共有エンジン (`auditor` / `false-positive-detector` / `fix-safety-checker`) に SKILL.md 固有の exclusion 既定と redundancy 判定 (他スキルとの被り) を追加してあります。

## 何をどの順番で行うか

収束するか `max_iterations` (既定 `5`) に達するまで以下を反復:

1. **Phase 1**: 対象 SKILL.md パス / `N` / `threshold` / `max_iterations` / 除外リストを `AskUserQuestion` で収集 (既定 `N=9` / `threshold=4` / `max_iterations=5`、除外には SKILL.md 固有の既定候補 — Claude Code 公式 `subagent_type` / `<this-skill-path>` placeholder 慣習 / cross-skill 参照 — を提示)
2. **Phase 1.5**: 各セクションの 1 行目的を draft → batch confirm (`fix-safety-checker` の intent baseline)
3. **Phase 2**: N 並列 `auditor` を `model: "sonnet"` で同一 turn dispatch (HIGH 重大度を最大 10 件/instance)
4. **Phase 3**: per-instance HIGH count + convergent issues (≥ threshold) の 2 表を生成
5. **Phase 4 / 4.5 / 4.6**: triage → `false-positive-detector` (REAL / FALSE / NEEDS_HUMAN) → `skill-md-redundancy-checker` (他スキル — skill-creator / skill-eval 等 — と被るか、KEEP / SIMPLIFY / REMOVE)
6. **Phase 5 / 5.5 / 5.6**: fix draft (single / multi-option) → `fix-safety-checker` (SAFE / NEEDS_REVIEW / UNSAFE) → `AskUserQuestion` で 1 件ずつ承認
7. **Phase 6**: `Edit` で適用
8. **Phase 7 / 8**: Phase 2 から再ディスパッチ → 収束判定 (全 N が clean / `(N − threshold + 1)` 以上が clean / HIGH 平均プラトー / max_iter / fix candidate 0)

## インストール

```
/plugin marketplace add almondoo/almondoo-claude-plugins
/plugin install skill-md-parallel-audit@almondoo-claude-plugins
```

## 使い方

```
/skill-md-parallel-audit:skill-md-parallel-audit
```

ユーザーが「この SKILL.md を audit して」「skill 仕様の曖昧さを潰したい」「skill quality を多エージェントでレビュー」などと依頼したときに、スキルが自動起動します。

## レイアウト

```
skill-md-parallel-audit/
├── .claude-plugin/
│   └── plugin.json
├── skills/
│   └── skill-md-parallel-audit/
│       ├── SKILL.md                            # メインのスキル定義
│       ├── agents/                             # 専門サブエージェント
│       │   ├── auditor.md                      # 共有 engine (copy)
│       │   ├── false-positive-detector.md      # 共有 engine (copy)
│       │   ├── fix-safety-checker.md           # 共有 engine (copy)
│       │   └── skill-md-redundancy-checker.md  # SKILL.md 固有
│       └── evals/
│           └── evals.json                      # トリガー / 振る舞いテスト
└── README.md
```

## claude-md-parallel-audit との違い

| 観点 | claude-md-parallel-audit | skill-md-parallel-audit |
|---|---|---|
| 対象ファイル | CLAUDE.md / AGENTS.md 系 | SKILL.md |
| Phase 1 exclusion 既定 | (なし) | Claude Code 公式 `subagent_type` / `<this-skill-path>` placeholder 慣習 / cross-skill 参照 |
| Phase 4.6 redundancy | Claude Code default system prompt と被るか | 他スキル (skill-creator / skill-eval 等) と被るか |
| 共有 engine (`auditor.md` / `false-positive-detector.md` / `fix-safety-checker.md`) | 同一 | 同一 (copy) |

## 関連プラグイン

- `claude-md-parallel-audit` ─ CLAUDE.md 系ファイル向けの sibling
- `skill-eval` ─ 構造スコアリング + dynamic A/B (本プラグインが補完する prose 監査と直交)

## ライセンス

[Apache-2.0](../../LICENSE)

# skill-md-parallel-audit

SKILL.md (Claude Code プラグインの skill 仕様ファイル) を **多エージェント並列監査** で曖昧さ / 矛盾 / 暗黙前提 / 未定義用語を検出するプラグイン。`claude-md-parallel-audit` の **sibling** であり、エンジン (auditor / false-positive-detector / fix-safety-checker) は共有しつつ、SKILL.md 固有の exclusion 既定 と redundancy 判定 (他スキルとの被り) を組み込み済み。

## 何をするか

1. **Phase 1**: target SKILL.md / N / threshold / max_iterations / exclusions を `AskUserQuestion` で収集 (exclusion には SKILL.md 固有の既定候補を提示)
2. **Phase 1.5**: 各セクションの 1 行目的を draft → batch confirm (fix-safety-checker の intent baseline)
3. **Phase 2**: N 並列 auditor を `model: "sonnet"` で同一 turn dispatch
4. **Phase 3**: per-instance HIGH count + convergent issues (≥ threshold) の 2 表を生成
5. **Phase 4 / 4.5 / 4.6**: triage → false-positive-detector → **skill-md-redundancy-checker** (他スキルとの被りを KEEP / SIMPLIFY / REMOVE 分類)
6. **Phase 5 / 5.5 / 5.6**: fix draft (single / multi-option) → fix-safety-checker → `AskUserQuestion` 1 件ずつ承認
7. **Phase 6**: `Edit` で適用
8. **Phase 7 / 8**: 再検証 → 収束判定

## claude-md-parallel-audit との違い

| 観点 | claude-md-parallel-audit | skill-md-parallel-audit |
|---|---|---|
| 対象ファイル | CLAUDE.md / AGENTS.md 系 | SKILL.md |
| Phase 1 exclusion 既定 | (なし) | Claude Code 公式 `subagent_type` (`general-purpose` 等) / `<this-skill-path>` placeholder 慣習 / cross-skill 参照 |
| Phase 4.6 redundancy | Claude Code default system prompt と被るか | 他スキル (skill-creator / skill-eval / 等) と被るか |
| 共有 engine (`auditor.md` / `false-positive-detector.md` / `fix-safety-checker.md`) | 同一 | 同一 (copy) |

`auditor.md` の 7 軸は `claude-md-parallel-audit` で実証済みのまま再利用 (skill-eval/SKILL.md への C 案試走で 9/9 convergence・低 false-positive を確認)。

## トリガー条件

ユーザが「この SKILL.md を audit して」「skill 仕様の曖昧さを潰したい」「skill quality を多エージェントでレビュー」などと依頼したとき (Claude のスキル自動トリガー経由) に発動。

## 前提

- subagent 並列実行を実行できる Claude Code 環境 (`Agent` ツール / `run_in_background: true`)
- `AskUserQuestion` ツール

## ディレクトリ構成

```
plugins/skill-md-parallel-audit/
├── .claude-plugin/plugin.json
├── README.md
└── skills/
    └── skill-md-parallel-audit/
        ├── SKILL.md
        ├── agents/
        │   ├── auditor.md                       # 共有 engine (copy)
        │   ├── false-positive-detector.md       # 共有 engine (copy)
        │   ├── fix-safety-checker.md            # 共有 engine (copy)
        │   └── skill-md-redundancy-checker.md   # SKILL.md 固有
        └── evals/
            └── evals.json
```

## 関連プラグイン

- `claude-md-parallel-audit` ─ CLAUDE.md 系ファイル向けの sibling
- `skill-eval` ─ 構造スコアリング + dynamic A/B (skill-md-parallel-audit が補完する prose 監査と直交)

# skill-eval

任意の Claude Code スキルを **2 層で評価する** プラグイン。

## 何をするか

1. **静的レイヤー (Static)** — スキルの構造を claude-code プラグイン規約に照らしてスコアリング。
   - frontmatter の妥当性 (`name` がディレクトリ名と一致するか / `description` に「いつトリガーするか」の手がかりが含まれるか / 長さが適正範囲か)
   - SKILL.md 本文の行数 (目安 500 行以内)
   - progressive disclosure の活用 (`references/` / `scripts/` / `assets/`)
   - 命令調のトーン / `MUST` や `NEVER` の濫用がないか

2. **動的レイヤー (Dynamic)** — **with-skill vs without-skill のサブエージェント A/B 実行** を行う。skill-creator と同じ方式。
   - 同一テストプロンプトを両構成で並列実行
   - assertion による採点 (pass rate)
   - 所要時間 (秒) / トークン消費の差分
   - `benchmark.json` + `benchmark.md` に集約

## トリガー条件

ユーザーが「このスキルを評価して」「with / without でベンチを取って」「このスキルの品質をスコア化して」などと依頼したとき (Claude のスキル自動トリガー経由) に発動します。スラッシュコマンドは提供しません。

## 前提

- Python 3.10+ (スクリプトは標準ライブラリのみで動作。`parse_frontmatter` は PyYAML が利用可能な場合に使用)

## ディレクトリ構成

```
plugins/skill-eval/
├── .claude-plugin/plugin.json
├── README.md
└── skills/
    └── skill-eval/
        ├── SKILL.md
        ├── scripts/
        │   ├── static_check.py         # 構造スコアリング
        │   ├── aggregate_benchmark.py  # with / without 結果の集約
        │   └── render_report.py        # static.json + benchmark.json → report.md
        ├── references/
        │   └── eval-axes.md            # 評価軸の詳細
        ├── agents/
        │   └── grader.md               # assertion 採点用プロンプトテンプレート (Claude Code agent ではない)
        └── evals/
            └── evals.json              # このスキル自身のテストケース
```

## 出力例

```
report.md          ... 人間向けレポート
static.json        ... 静的スコアリング結果
benchmark.json     ... with / without の集約結果 (skill-creator 互換スキーマ)
runs/eval-N/
  with_skill/outputs/...
  without_skill/outputs/...
```

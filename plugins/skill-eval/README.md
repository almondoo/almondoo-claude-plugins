# skill-eval

任意の Claude Code skill を **二層構造で評価** するプラグイン。

## 何をするか

1. **Static 層** — claude-code プラグイン規約に基づいて skill そのものの構造を採点する。
   - frontmatter の妥当性 (`name` がディレクトリ名と一致 / `description` が "when to trigger" を含む / 長さ妥当)
   - SKILL.md 本体の長さ (~500 行目安)
   - Progressive disclosure (`references/` / `scripts/` / `assets/` を活用しているか)
   - 命令調 (imperative) で書かれているか / `MUST` / `NEVER` の濫用がないか

2. **Dynamic 層** — skill-creator と同じ手法で **with-skill / without-skill の subagent A/B 実行** を行う。
   - 同じテストプロンプトを 2 系統並列実行
   - assertion 採点 (pass rate)
   - 時間 (秒) / トークン消費の delta
   - benchmark.json + benchmark.md にまとめる

## いつ起動するか

ユーザーが "この skill を評価して" / "with vs without でベンチして" / "skill の品質を採点して" などと頼んだとき (Claude の skill auto-trigger 経由)。スラッシュコマンドは持たない。

## 前提

- Python 3.10+ (scripts は stdlib のみで動作。PyYAML があれば parse_frontmatter で利用)

## ディレクトリ構成

```
plugins/skill-eval/
├── .claude-plugin/plugin.json
├── README.md
└── skills/
    └── skill-eval/
        ├── SKILL.md
        ├── scripts/
        │   ├── static_check.py         # 構造採点
        │   ├── aggregate_benchmark.py  # with/without 結果集約
        │   └── render_report.py        # static.json + benchmark.json → report.md
        ├── references/
        │   └── eval-axes.md            # 評価軸の詳細
        ├── agents/
        │   └── grader.md               # assertion 採点プロンプトテンプレート (Claude Code agent ではない)
        └── evals/
            └── evals.json              # 本 skill 自身のテストケース
```

## 出力例

```
report.md          ... 人間向けレポート
static.json        ... 静的採点結果
benchmark.json     ... with/without 集約結果 (skill-creator 互換スキーマ)
runs/eval-N/
  with_skill/outputs/...
  without_skill/outputs/...
```

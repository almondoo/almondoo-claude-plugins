# skill-eval

任意の Claude Code スキルを **2 つのレイヤー** で評価するプラグイン —— 静的な構造品質と、with-skill vs. without-skill の動的 A/B ベンチマーク。さらに、評価結果のワークスペースをデザインされた HTML レポートに描画する sibling の viewer スキルを同梱しています。

## 何をするか

1. **静的レイヤー** —— claude-code プラグイン規約に対してスキルの構造をスコアリング。
   - frontmatter の妥当性 (`name` がディレクトリ basename に一致するか、`description` に when-to-use の手がかりが含まれるか、公式の 1,536 文字上限とコミュニティの 50 文字下限の範囲内か)
   - SKILL.md 本文の長さ (目安として 500 行以下)
   - progressive disclosure (`references/` / `scripts/` / `assets/` / `agents/` / `prompts/`)
   - 命令形のトーン、`MUST` / `NEVER` / `ALWAYS` マーカーの密度 (各々に正当な理由があることが期待される)

2. **動的レイヤー** —— **with-skill vs. without-skill のサブエージェント A/B** を実行 (`skill-creator` の方式を踏襲)。
   - 同一の eval プロンプトを単一 turn 内で両構成について並列ディスパッチ
   - アサーションベースの採点 (pass rate)
   - 時間 (秒) と token 消費の差分
   - `benchmark.json` + `benchmark.md` に集約

3. **改善提案の導出** —— `report.md` の "Top issues to fix" は 4 つの情報源 (static FAIL / 識別力のあるアサーション / time-token-variance の異常 / dogfooding gap) から、結果を変える反実仮想性を優先して手書きで構成します。詳細は `skills/skill-eval/references/proposal-derivation.md`。

4. **HTML レンダリング** —— sibling の `skill-eval-viewer` スキルがワークスペース (`report.md` + `static.json` + `benchmark.json` + `NN-*.md` のサブレポート) を単一の self-contained な HTML ファイルにレンダリング。オプションの `--serve` モードは `127.0.0.1` でローカル HTTP サーバーをバインドします。

## 用語集

レポートやドキュメントで頻出する用語の意味。HTML レポートからは省略しているため、初見の読者はここを参照してください。

- **Static 層 (static layer)** — SKILL.md の構造を機械的に採点する層。frontmatter の有無・本文行数・進行的開示などを確認する。
- **Dynamic 層 (dynamic layer)** — 実プロンプトを skill あり / なしで並列実行し、出力を assertion で採点・比較する層。
- **A/B benchmark** — 同じプロンプトを 2 条件 (with_skill / without_skill) で同時に走らせ、結果を比較する手法。Dynamic 層が採用している方式。
- **with_skill / without_skill** — subagent に対象 skill の SKILL.md を読ませた条件 (with_skill) と、読ませない条件 (without_skill = デフォルト動作のままの subagent)。
- **hard_fail** — Static 層で frontmatter 不在など出荷停止級の欠陥が検出された状態。スコアを 0.4 にキャップし、Dynamic 層をスキップする。
- **pass_rate delta** — with_skill と without_skill の pass_rate (assertion 合格率) の差。+0.2 以上で Ship-ready 条件の 1 つを満たす。
- **差別化アサーション (differentiating assertion)** — with_skill だけが通る (もしくは without_skill だけが通る) assertion。skill の効果を可視化する。
- **runs_per_configuration** — 1 条件あたりの試行回数。variance を計測するなら 3 以上が推奨。
- **iteration** — skill-eval を 1 回流したサイクル。workspace 下の `iteration-N/` に成果物が全て入る。
- **verdict** — 判定。`Ship-ready` / `Needs work` / `Net negative` / `Inconclusive` のいずれか。Ship-ready は static ≥ 0.8 かつ pass_rate delta ≥ +0.2、Net negative は delta < 0 もしくは time と tokens がともに 2 倍以上、Inconclusive は variance が高い場合の追加フラグ。

## いつ起動するか

Claude の自動スキルトリガーで起動します。ユーザーが「このスキルを評価して」「with vs. without でこのスキルをベンチマークして」「このスキルを claude-code プラグイン規約に照らして監査して」「このスキルって良いの?」のような依頼をしたときが該当します。スラッシュコマンドは提供しません。

viewer スキルは、skill-eval ワークスペースを HTML にレンダリングしたり、評価レポートを視覚的に共有したりする依頼でトリガーされます。

## 要件

- Python 3.10+ (スクリプトは標準ライブラリで動作。`parse_frontmatter` は PyYAML が利用可能なら opportunistic に使用)

## ディレクトリレイアウト

```
plugins/skill-eval/
├── .claude-plugin/plugin.json
├── README.md
└── skills/
    ├── skill-eval/                   # 評価器本体
    │   ├── SKILL.md
    │   ├── scripts/
    │   │   ├── static_check.py       # 構造スコアリング
    │   │   ├── aggregate_benchmark.py # with / without 集約
    │   │   └── render_report.py      # static.json + benchmark.json → report.md scaffold
    │   ├── references/
    │   │   ├── eval-axes.md          # 軸別の根拠
    │   │   ├── step-3-dispatch.md    # サブエージェントディスパッチの完全形
    │   │   ├── step-4-grading.md     # grader 契約と grading.json スキーマ
    │   │   ├── step-5-aggregation.md # benchmark.json スキーマと欠損データのセマンティクス
    │   │   └── proposal-derivation.md # "Top issues to fix" の導出ガイド
    │   ├── agents/
    │   │   └── grader.md             # grader サブエージェント用のプレーンなプロンプトテンプレート (ディスパッチ可能な agent ファイルではない)
    │   └── evals/
    │       └── evals.json            # このスキル自身のテストケース
    └── skill-eval-viewer/            # HTML レンダラー
        ├── SKILL.md
        ├── references/frontend-design.md
        └── scripts/
            └── render_html.py        # workspace → report.html (file または --serve モード)
```

開発履歴・設計判断は plugin の外、リポジトリ root の `docs/learnings/skill-eval.md` に分離されています (インストール時の配布対象外)。

## 出力アーティファクト (反復ごと)

```
<workspace>/iteration-N/
├── evals.json                    # この反復のプロンプトとアサーションの source of truth
├── static.json                   # 静的レイヤーのスコア
├── benchmark.json                # 動的レイヤー集約 (skill-creator 互換スキーマ)
├── benchmark.md                  # 人間可読のサマリー表
├── report.md                     # 最終的な人向けレポート (verdict + Top fix + ファイル一覧)
├── report.html                   # オプション、skill-eval-viewer が生成
└── runs/eval-N/
    ├── with_skill/    { outputs/, grading.json, timing.json }
    └── without_skill/ { outputs/, grading.json, timing.json }
```

## 関連

- `skills/skill-eval/SKILL.md` —— 完全なスキル仕様 (入力、6 ステップワークフロー、verdict ヒューリスティック、proposal-derivation へのポインタ)
- `skills/skill-eval-viewer/SKILL.md` —— viewer の契約 (ワークスペース入力、ファイル vs. serve 配信モード、デザインノート)
- リポジトリ root の `docs/learnings/skill-eval.md` —— 設計判断、反復履歴、既知のフォローアップ (plugin 外、配布対象外)

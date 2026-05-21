---
name: skill-eval
description: Evaluate any Claude Code skill on two layers — (1) static structural quality derived from claude-code plugin conventions (frontmatter validity, body length, progressive disclosure, description triggerability) and (2) dynamic A/B benchmarking that runs the same prompts in parallel subagents with-skill vs without-skill and compares pass rate, time, and tokens. Use whenever the user wants to evaluate, audit, benchmark, A/B test, score, or measure the quality of a skill, or when they ask "is this skill any good", "does this skill actually help", or "compare with and without this skill".
---

# skill-eval

任意の Claude Code skill を **static + dynamic の二層** で評価し、人間向けレポートと機械可読な JSON を出力する。

評価対象は SKILL.md を 1 つ含むディレクトリ。プラグイン (`.claude-plugin/plugin.json` 配下の `skills/*`) 単体の skill ディレクトリのどちらでも受け取れる。

---

## なぜ二層なのか

- **Static だけ**だと "綺麗に書かれているが実際は役に立たない skill" を見逃す。
- **Dynamic だけ**だと、たまたま LLM が頑張って合格しただけの skill を「良い」と判定してしまい、配布された他人の環境で再現しないリスクがある。さらに、構造上の負債 (本体が長すぎる / 命令調過多 / progressive disclosure を使っていない) は実行ベンチでは見えない。
- 両方を出すことで、「静的にも筋が良く、かつ実測でも with > without の差が出ている」という基準で skill を judge できる。

評価軸の詳細は `references/eval-axes.md`。`MUST` / `NEVER` を使わずに why を書く skill が良い、という思想は claude-code-plugin 規約 (Anthropic skill-creator の "Writing Style" 節) と整合させている。

---

## 入力

ユーザーから以下を聞き取る (既に明示されていれば省略):

1. **target_skill_path** (必須) — 評価したい skill のディレクトリ。例: `/path/to/plugins/foo/skills/foo/`。SKILL.md が直下に必要。
2. **eval prompts** (任意) — テストプロンプト。未指定なら static 結果と SKILL.md の description から 3 件を自動生成して確認を取る。
3. **runs_per_configuration** (任意) — A/B 各構成の試行回数。デフォルト 1。分散を見たいときだけ 3 を提案。
4. **skip dynamic?** (任意) — Static だけで良いと言われたら dynamic 層をスキップ。

聞くときは AskUserQuestion を使う (テキスト出力で聞かない)。

---

## ワークフロー全体像

```
[Step 1] static_check.py で構造採点 → static.json
[Step 2] eval prompts を確定 (ユーザー提示 or 自動生成して合意)
[Step 3] 各 prompt について with_skill / without_skill subagent を同一ターンで並列 dispatch
[Step 4] 出力を grader (agents/grader.md) で assertion 採点 → grading.json
[Step 5] aggregate_benchmark.py で benchmark.json + benchmark.md を生成
[Step 6] static + dynamic を合体した report.md を書く
```

ワークスペースは target_skill_path のサイドに `<skill-name>-eval-workspace/iteration-N/` を作る。skill-creator のレイアウトを意識しているので、後で skill-creator に持ち込んで iterate もできる。

---

## Step 1: Static 採点

`scripts/static_check.py` を実行する:

```bash
python3 <this-skill-path>/scripts/static_check.py <target_skill_path> \
  --out <workspace>/iteration-N/static.json
```

採点軸 (実装と 1:1 対応、詳細は `references/eval-axes.md`):

| 軸 | 内容 | 重み |
|---|---|---|
| frontmatter.name_matches_dir | `name:` がディレクトリ名と一致 (公式仕様では omission も mismatch も合法なので **warn**) | warn |
| frontmatter.description_present | description が空でない | hard fail if no |
| frontmatter.description_has_trigger | description が "when to use" の手がかりを含む (動詞 + 文脈) | warn |
| frontmatter.description_length | 公式上限は `description + when_to_use` 合算 1,536 字 (skills.md)。下限 50 は community heuristic | warn 外れたら |
| body.line_count | 本体 (frontmatter 後) の行数 ≤ 500 | warn over |
| body.must_never_density | `MUST` / `NEVER` / `ALWAYS` の出現密度 (コードスパン除外)。高すぎる ≒ why が書かれていない兆候 | warn |
| body.no_emoji | 本体に絵文字 (U+1F300-1FAFF) が混入していない。技術記号 (→ ✓ ★ 等) は対象外 | warn |
| structure.has_progressive_disclosure | references/ scripts/ assets/ のいずれかが存在 | info (body が短ければ不要) |
| structure.scripts_referenced_from_body | scripts/ のファイルが SKILL.md から参照されている | warn unreferenced |
| structure.references_referenced_from_body | references/ も同上 | warn unreferenced |

**hard_fail のセマンティクス**: severity=`hard_fail` の軸が 1 つでも fail すると、`hard_fail: true` がフラグされ score が 0.4 にキャップされる (ship-blocker の数学的反映)。
**frontmatter が無い場合**: `frontmatter.present` (severity=hard_fail) のみが追加され、他の frontmatter 系チェックは skip される。

`static_check.py` は配点を `static.json` に書き出す。例:

```json
{
  "target": "/path/to/skill",
  "score": 0.82,
  "checks": [
    {"axis": "frontmatter.name_matches_dir", "passed": true, "evidence": "..."},
    {"axis": "body.must_never_density", "passed": false, "evidence": "23 occurrences in 180 lines (>10/100)"}
  ],
  "hard_fail": false,
  "warnings": 2
}
```

`hard_fail: true` の場合は dynamic 層を実行せず、修正を促す。

---

## Step 2: Eval prompts の確定

`<target>/evals/evals.json` がもう存在するならそれを採用する。なければ:

1. SKILL.md の description と body から **3 件** のテストプロンプトを生成
2. AskUserQuestion で「この 3 件で評価して良いか」を確認 (修正 / 追加 / OK)
3. 確定したら `<workspace>/iteration-N/evals.json` に保存

プロンプトを書くときの注意 (skill-creator の Description Optimization 節と同じ思想):

- 抽象的 (`"Format this data"`) ではなく、ユーザーが実際にタイプしそうな具体性 (ファイル名・列名・背景) を入れる
- skill が真価を発揮する **multi-step / specialized** な題材を選ぶ (one-shot で誰でも解けるものは差が出ない)
- skill の description が想定していない「近傍タスク」も 1 件混ぜると、過剰トリガーや誤適用の検出に役立つ

各プロンプトに assertion を 2〜4 件付ける:

```json
{
  "evals": [
    {
      "id": 1,
      "name": "extract-table-from-quarterly-pdf",
      "prompt": "Q4 sales final FINAL v2.xlsx を CSV 化して...",
      "assertions": [
        {"text": "出力に Revenue 列が含まれる", "kind": "factual"},
        {"text": "金額が数値型として保存されている", "kind": "format"}
      ]
    }
  ]
}
```

---

## Step 3: A/B 並列 dispatch

**重要: 同一ターンで全 prompt × 2 構成を並列 dispatch する。** 後追いで baseline を回すと条件 (時刻・モデル混雑) がずれて比較性が落ちる。

各 prompt について 2 つの Agent (`subagent_type: general-purpose`) を `run_in_background: true` で launch:

### with-skill subagent

```
Execute this task. You have access to the following skill - read its SKILL.md first
and follow it for the task:

Skill SKILL.md path: <target_skill_path>/SKILL.md

Task: <eval prompt>

Save all outputs (files, final answer) under:
<workspace>/iteration-N/runs/eval-<id>/with_skill/outputs/

When done, write a short summary to outputs/SUMMARY.md describing what you produced.
```

### without-skill subagent

```
Execute this task WITHOUT using any special skill or external reference. Use only
your default tools.

Task: <eval prompt>

Save all outputs under:
<workspace>/iteration-N/runs/eval-<id>/without_skill/outputs/

When done, write a short summary to outputs/SUMMARY.md describing what you produced.
```

タスク完了通知 (Agent ツールの返り値 `<usage>` ブロック) に含まれる `total_tokens` と `duration_ms` を **即時** に `<run-dir>/timing.json` へ保存する。完了通知が一度過ぎると後から取得できないため、子 agent ごとに通知を受け取った直後に write すること。

```json
{ "total_tokens": 84852, "duration_ms": 23332, "total_duration_seconds": 23.3 }
```

`timing.json` が無い run は aggregator 側で `null` として扱われ stats から除外される (見せかけの 0 にはならない)。

### dispatch の判断基準

- 評価対象 skill が **read-only / safe** であることを SKILL.md ざっと読みで確認。外部書き込み (PR 作成・メール送信等) を含む skill は subagent ではなく sandbox 化を必要とする (現状はユーザーに警告して dynamic 層スキップを提案)。
- prompt × 構成 が多い (例: 3 × 2 × 3 試行 = 18) と並列度が暴れるので、`runs_per_configuration > 1` のときは 6 並列ずつバッチに分ける。

---

## Step 4: Grader による採点

全 run 完了後、`agents/grader.md` (これは frontmatter 無しの**プロンプトテンプレート**で、Claude Code agent ではない) を subagent に Read させるか、または inline で内容を貼り付けて各 run の outputs を assertion と突き合わせる。

grader への入力例:

```
Read this prompt template: <this-skill-path>/agents/grader.md (absolute path)
Apply it to grade this run:
  Run directory: <workspace>/iteration-N/runs/eval-<id>/with_skill/
  Assertions: <full list from evals.json>
Write grading.json to the run directory.
```

`grading.json` の schema (skill-creator viewer 互換):

```json
{
  "expectations": [
    {"text": "...", "passed": true,  "evidence": "..."},
    {"text": "...", "passed": false, "evidence": "..."}
  ],
  "summary": {"passed": 1, "failed": 1, "total": 2, "pass_rate": 0.5}
}
```

フィールド名 (`expectations` / `text` / `passed` / `evidence` / `summary`) はすべて aggregator と viewer が key で読むので変えない。

プログラム的に検証できる assertion (ファイル存在・正規表現一致など) は grader に「スクリプトを書いて確かめろ」と促す。eyeballing は遅くて不安定。

---

## Step 5: 集約

`scripts/aggregate_benchmark.py` を実行:

```bash
python3 <this-skill-path>/scripts/aggregate_benchmark.py \
  <workspace>/iteration-N \
  --skill-name <target-skill-name> \
  --out <workspace>/iteration-N/benchmark.json
```

`benchmark.json` のスキーマは skill-creator の `references/schemas.md` と同一 (`runs[]` / `run_summary.with_skill` / `run_summary.without_skill` / `delta`)。

`benchmark.md` も併せて生成して人間が読みやすいテーブルにする:

```
| eval | with pass | without pass | Δ pass | with sec | without sec | Δ tokens |
| 1    | 1.00      | 0.33         | +0.67  | 42       | 30          | +1700    |
```

---

## Step 6: 統合レポート

`scripts/render_report.py` を使えば `static.json` / `benchmark.json` から `report.md` の骨組みを自動生成できる:

```bash
python3 <this-skill-path>/scripts/render_report.py \
  --static <workspace>/iteration-N/static.json \
  --benchmark <workspace>/iteration-N/benchmark.json \
  --out <workspace>/iteration-N/report.md
```

`--benchmark` は省略可 (static のみのレポートになる)。生成後は verdict と上位修正候補を手で書き足す。

テンプレを使わず手書きするときの最小形式:

```markdown
# skill-eval report: <skill-name>

## Verdict
<one-line: "Ship-ready" / "Needs work" / "Net negative" / "Inconclusive" のいずれか>

## Static (score: <0.0-1.0> / hard_fail: <true|false>)
- 各 axis の pass/fail と evidence を箇条書き

## Dynamic
| metric | with_skill | without_skill | Δ |
| pass_rate | 0.83 | 0.33 | +0.50 |
| time (s) | 42.5 | 32.0 | +10.5 |
| tokens | 3800 | 2100 | +1700 |

## Differentiating assertions
- 各 differentiating assertion text と (eval_name, with_rate, without_rate)

## Top issues to fix
1. (static 由来 + dynamic 由来の up-to 3 件)

## Files
- static.json / benchmark.json / runs/eval-*/{with_skill,without_skill}/outputs/
```

verdict は以下のヒューリスティクスで決める (絶対視せず、ユーザーに最終判断を委ねる):

- **Ship-ready**: static score ≥ 0.8 かつ pass_rate delta ≥ +0.2
- **Needs work**: static score 0.5〜0.8 or pass_rate delta が +0.05〜+0.2
- **Net negative**: pass_rate delta ≤ 0 か、time/tokens がともに 2 倍以上に膨らんでいる
- **Inconclusive**: 試行数不足や variance が高い (stddev > mean*0.3)

---

## ユーザーとの対話

評価作業はそれなりに時間がかかる (subagent 並列で典型 1〜3 分 × prompt 数)。以下を守る:

- **着手前に 1 文で計画を提示**: 「target=X / prompts=3件自動生成 / runs=1 / 推定 90 秒」
- **dispatch 直後にひとこと**: 「6 個の subagent を launch しました。完了次第 grader に流します」
- **完了時に report.md を必ず提示**: 単体の数字だけ出すとユーザーは判断できない。verdict と「上位 3 件の修正候補」まで書く

判断を求めるときは AskUserQuestion を使う (テキストで質問しない)。

---

## エッジケース

- **target_skill_path に SKILL.md がない**: hard fail。プラグインルートを渡された可能性があるので、`skills/*/SKILL.md` を glob して候補を提示する。
- **evals.json が既存だが assertion が空**: skill-creator と同じく、prompt から提案して合意を取る。
- **dynamic 層でどちらの構成も pass_rate 0**: prompt が難しすぎる/曖昧すぎる可能性が高い。prompt を見直すべきと report に書く。
- **with_skill が without_skill に負ける**: skill が逆効果。assertion の質を疑う前に SKILL.md を読み返し、何を強制しているかを確認 (`MUST` で誤った手順を強要しているなど)。

---

## 拡張案 (未実装)

- skill 単体ではなく **plugin 全体** (`plugin.json` + 配下の commands/agents/hooks/skills) を一括採点
- description optimization (skill-creator の `run_loop.py` と同思想で trigger eval を回す)
- 複数 skill を横並びでベンチして leaderboard を吐く

これらは別 skill / 別 plugin として切る方が責務が明確。

---

## 参考

- claude-code plugin の SKILL.md / frontmatter / progressive disclosure 規約 → claude-plugins-official `skill-creator` の SKILL.md "Writing Style" / "Skill Writing Guide" 節
- A/B benchmark 手法と JSON スキーマ → claude-plugins-official `skill-creator` の `references/schemas.md`
- 評価軸の詳細 → `references/eval-axes.md`

# Evaluation Axes — 詳細

skill-eval が出すスコアの根拠と、各軸を選んだ理由。`SKILL.md` の表を一段深掘りした参照ドキュメント。

---

## Static 層

### なぜ static を測るのか

dynamic ベンチで「with > without」が出ても、それは LLM が頑張った結果かもしれない。SKILL.md の構造が悪い skill は:

- 配布先の環境で再現しない (依存ツールが暗黙)
- 将来の Claude モデルで挙動が変わったとき直しにくい
- 他人が読んで「いつ呼ぶべきか」が分からない

これらは実測ベンチでは見えないので静的に押さえる必要がある。

---

### frontmatter

| axis | 意図 | 失敗時の典型原因 |
|---|---|---|
| `frontmatter.present` | YAML frontmatter があるか。ない skill は Claude Code の skill loader が読まない | `---` を書き忘れた / フォーマットミス |
| `frontmatter.name_matches_dir` | `name:` がディレクトリ名と一致しないと plugin の skill 発見ロジックが破綻する | リネーム時に name を更新し忘れた |
| `frontmatter.description_present` | description は triggering の唯一の判断材料。空だと一生呼ばれない | template から消し忘れ |
| `frontmatter.description_has_trigger` | description が「何をするか」だけで「いつ使うか」を書いていないと under-trigger になる (公式 skill-creator が指摘) | 「Format data」のような抽象表現 |
| `frontmatter.description_length` | Anthropic は `description + when_to_use` 合算で **1,536 字** を上限としている (skills.md § Skill descriptions are cut short)。下限 50 字は短すぎる description が under-trigger になる傾向からの community heuristic | 説明過多 / 過少 |

#### description の良し悪し

公式 skill-creator の例:

- ❌ `"How to build a dashboard"` — 何をするかは分かるが「いつ」が無い
- ✅ `"How to build a simple fast dashboard to display internal Anthropic data. Make sure to use this skill whenever the user mentions dashboards, data visualization, internal metrics, or wants to display any kind of company data, even if they don't explicitly ask for a 'dashboard.'"` — when/what/edge-case が揃っている

skill-eval は trigger 語彙 (`when` / `use` / `whenever` / `if` / `before` / `after` / `trigger`) の出現で簡易判定するが、これは proxy なので過信しない。最終判断は人間が `report.md` を見て決める。

---

### body

| axis | 意図 |
|---|---|
| `body.line_count` | 公式ガイドの目安 ≤ 500 行。本体が長いと毎回 context を食う上、Claude が読み飛ばすリスクが高い |
| `body.must_never_density` | `MUST` / `NEVER` / `ALWAYS` が多い skill は「なぜそうすべきか」を説明していない兆候。コードスパン内 (バックティック / fenced block) の出現はメタ言及とみなし除外する |
| `body.no_emoji` | Anthropic の global "Only use emojis if the user explicitly requests it" 規約。skill 本体での絵文字使用は出力にも伝染しやすく、ユーザーの好みを超えて干渉する。コードスパン内は除外 (チェックボックス記号などの説明用途は許容) |

#### why density matters

公式 skill-creator の Writing Style 節:

> Try to explain to the model why things are important in lieu of heavy-handed musty MUSTs. Use theory of mind and try to make the skill general and not super-narrow to specific examples.

`MUST` を多用すると:

- LLM が言葉の意味を「ルール」として字句通り守ろうとし、edge case で柔軟性を失う
- 著者が why を考えていない兆候。後で別の Claude モデルが読むと挙動が割れる
- skill の総量が伸びる (each rule needs its own line)

10/100 行を超えるとカウントが上がりすぎ。これは経験則。

---

### structure

| axis | 意図 |
|---|---|
| `structure.has_progressive_disclosure` | 本体が長いなら `references/` / `scripts/` / `assets/` に分割すべき。短い skill (~100 行) なら不要 |
| `structure.scripts_referenced_from_body` | scripts/ にあるのに本体から参照されていないスクリプトはデッドコード。`scripts/foo.py` を本体で名前出ししているかを確認 |
| `structure.references_referenced_from_body` | 同上 |

scripts/references が本体から呼ばれていないと、Claude は読み込まないので 100% 役に立たない (load-on-demand)。

---

## Manual 観点 (機械化未実装、レビュアー向けチェックリスト)

iteration-2 の baseline (without-skill 評価) が指摘した観点のうち、機械化が難しいものを記録する。`static_check.py` には含まれないが、人間レビューや LLM grader に渡すプロンプトでは観点として有用。

| axis | チェック方法 | なぜ機械化していないか |
|---|---|---|
| `tool_usage_explicit` | SKILL.md の各手順ステップで、使うべきツール (Read / Edit / Bash 等) が明示されているか | 「ステップ」の境界をパースする決定的方法がない (見出し階層・番号付きリスト等の表現が skill 著者で違う) |
| `cross_file_consistency` | SKILL.md / plugin.json / README.md / marketplace.json でカテゴリ数・既定値・skill 名が一致するか | プラグインごとに「整合すべきフィールド」が違うので一般化が難しい |
| `destructive_ops_safety_alignment` | 破壊的操作のデフォルトが deny / ask になっており、global CLAUDE.md の Tier-3 と整合しているか | 「何が破壊的か」の判定は LLM 推論が必要 |
| `output_format_specified` | 出力ファイルのフォーマット (JSON schema・ファイル名・改行など) が明示されているか | "明示" の閾値が曖昧 |

これらは LLM grader (将来) を回す際にプロンプトへ含めるためのリストとして残す。

---

## Dynamic 層

### なぜ A/B で測るのか

「skill が役に立っているかどうか」は同じプロンプトを skill 有り/無しで走らせて初めて分かる。skill-creator の benchmark 機構と同じ思想。

### 観測する指標

| metric | 何を意味するか | 良し悪し |
|---|---|---|
| `pass_rate` delta | with - without。skill の付加価値そのもの | +0.2 以上で「明確に価値あり」 |
| `time_seconds` delta | with の方が遅くなりがち (skill を読む分) | +30 秒くらいまでは許容、それ以上は body 圧縮の余地 |
| `tokens` delta | with の方が消費が多い | pass_rate 改善とのトレードオフで判断 |
| stddev | 分散。3 run 以上回したときに見る | mean × 0.3 を超えるなら flaky |
| `differentiating_assertions` | with-skill だけが通せた assertion | これが 0 件なら skill は実質効いていない |

### 注意点

- **with の方が遅いのは正常** — skill 本体を context に積む分、初動が遅れる。問題は遅さよりも pass_rate に見合っているか
- **without_skill が完璧に通る場合** — その task は Claude が単独で解けるので、その skill の存在意義をプロンプト選定から見直すべき
- **with_skill が悪化** — skill が誤った手順を強制している可能性が高い (`MUST` で間違ったやり方を矯正している等)

---

## verdict ヒューリスティクス

`SKILL.md` で言及した判定ロジックの根拠:

| verdict | 条件 | 直感 |
|---|---|---|
| **Ship-ready** | static ≥ 0.8 かつ pass_rate delta ≥ +0.2 | 静的にもまともで、効果も実測される |
| **Needs work** | 上記未満で、明らかに net negative ではない | 配布前にもう一段の改善余地 |
| **Net negative** | pass_rate delta ≤ 0、または time × 2 以上 & token × 2 以上 | skill 無しの方が良い |
| **Inconclusive** | runs_per_configuration < 3 または stddev > mean × 0.3 | サンプル不足 / 分散が大きい |

これらは絶対値ではない。例えば `time delta +200s` でも pass_rate が +0.6 上がるなら ship する価値はある。最終判断はユーザー。

---

## 参考リンク

- claude-plugins-official `skill-creator/SKILL.md` の "Skill Writing Guide" と "Description Optimization" 節
- claude-plugins-official `skill-creator/references/schemas.md` (benchmark.json スキーマ)

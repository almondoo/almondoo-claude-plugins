# Learnings — skill-eval

各セッションで得た知見を新しい順に記録。

## 2026-05-22 (Phase 0 integration + full audit-driven refinement)

### 設計判断

- **Phase 0 integration pattern が確立**: 他 skill (例: `skill-md-parallel-audit`) が `scripts/static_check.py` を pre-audit gate として呼ぶ pattern。`hard_fail` true で audit 中止 / 構造軸の auditor 重複防止 / N defaults 自動 suggest の 3 役割。
- **input vs output schema 分離は意図的**: `evals.json` は input = `assertions: [{text, kind}]`、grader 出力 = `expectations: [{text, passed, evidence}]`。混同すると aggregator/viewer の field-name 一致が壊れる (v0.1.3 で実害修正済)。
- **verdict heuristics は precedence ordering + additive Inconclusive**: 旧 unordered 4 verdict 表は boundary overlap (例: score=0.8 で Ship-ready と Needs work 両成立) を生んでいたため、first-match wins と additive variance flag に再構成 (v0.1.4)。

### 気付き / gotcha

- **`agents/` ディレクトリは progressive_disclosure 軸に含まれない**: `static_check.py` の `structure.has_progressive_disclosure` は `references/` `scripts/` `assets/` のみチェック。`agents/` を使う skill は実質 score 上限 0.968 で頭打ち。`info` severity のため hard_fail にはならないが、Phase 8 ship-ready criterion (`score=1.0`) は到達不可。
- **Translation 起因の ambiguity が頻発**: JP→EN 翻訳で 「on the day」(when?) / 「when_to_use」(spec に存在しない field 参照) / asymmetric sample table / placeholder 引用符ネスト等を引き継ぐ。翻訳直後の re-read が有効。
- **`(N − threshold + 1)` 式が practical convergence の正解**: 旧 「≥3/9 say clean」 は loose (残り 6 instance に reproducible 残存可)、`(9−4+1)=6` で「残り (threshold−1)=3 instance では reproducible 不成立」を数学的保証。

### 残課題

- `static_check.py` の `structure.has_progressive_disclosure` 軸を `agents/` 認識に拡張すべきか (現状ほぼ全 skill が 0.968 ceiling)。

### バージョン経緯

- v0.1.2 (initial) → v0.1.3 (`expectations` → `assertions` schema 整合) → v0.1.4 (workspace path / verdict heuristics / hard_fail flow / schema inlining / batch units の 5-fix)。

## 2026-05-21 (initial release)

- 多層評価 (static 構造 + dynamic A/B) を組み合わせたスキル評価ツール初回リリース (v0.1.2)。
- `scripts/{static_check,aggregate_benchmark,render_report}.py` + `agents/grader.md` + `references/eval-axes.md` の 4 部品構成。

# Learnings — claude-md-parallel-audit

各セッションで得た知見を新しい順に記録。

## 2026-05-22 (full-test iter-2/iter-3 verification + sibling 分離)

### 設計判断

- **Multi-agent audit は asymptotic, not zero**: iter 重ねると HIGH avg は initial 下降後 reflate (fix 適用が新 wording → 新 finding を誘発)。iter-3 で avg 8.1、practical convergence (≥6/9 clean) 到達せず。**2-3 iter が実用上限**、それ以上は新規変動が他既存 wording 経由でゼロ和。残存 ≥4/9 findings は "known asymptote" として受容。
- **`≥(N − threshold + 1)` 式に修正**: 旧 「≥3 of N 報告 NO HIGH ISSUES」は数学的に loose。default N=9/threshold=4 → ≥6/9 clean で「残り (threshold−1)=3 instance が同一 issue を flag しても reproducible 不成立」を保証 (v0.2.0)。
- **Phase 6a/6b split は cmpa 固有**: auto-mode classifier (`~/.claude/CLAUDE.md` Tier 2) に Edit 拒否された時用に "Yes, update my `<file>`" template playbook を 6b に集約。SKILL.md 系 sibling (smpa) は plugin artifact 扱いで classifier 非対象なので Phase 6 統合可。
- **Sibling として `skill-md-parallel-audit` を分離**: SKILL.md 専用 exclusion defaults + 別 redundancy-checker を sibling 化。engine 3 ファイル (auditor / fp-detector / fix-safety-checker) は byte-for-byte copy で共有。

### 気付き / gotcha

- **N=9 iter cost 実測 ~440k tokens**: Phase 2 sonnet 9×~32k ≈ 290k + verifiers (Phase 4.5 + 4.6) ~60k + Phase 5.5 safety-checker(s) ~30-90k。5-iter audit ≈ 1.5-2M。Phase 1 で必ず surface する。
- **Subagent は global CLAUDE.md の "use Glob/Grep" 規約を継承しない**: Bash `find` / `grep` を使ってしまう subagent が複数観察された。気になる場合は dispatch prompt で明示。
- **Subagent shared blind spots (頻出)**: 公式 `subagent_type` 名を "undefined" flag / 文書化済み override (`model: "sonnet"` Phase 2) を CLAUDE.md 違反と flag / Phase 6a/6b 知らず "Phase 6" を ambiguous と flag。Phase 1 exclusion defaults + iteration-history accumulated exclusion で抑制必須。
- **`(N − threshold + 1)` rationale の伝達難**: 数学的に正しいが「remaining (threshold−1) instance が同一 issue を flag しても reproducible 不成立」premise を unstated と auditor が flag し続ける (iter-3 で 9/9 該当)。式に説明文を添えるべき。

### iter-3 未解決 convergent (asymptote)

- L284 formula rationale 説明不足 (9/9)
- L136 skip range Phase 8 含意 / Phase 5 ambiguous (9/9)
- L326 Tool Requirements Phase 5.5 dispatch foreground+parallel 矛盾 (9/9)
- L203 `rule_burden_impact` field 定義が agent file 側のみ (6/9)
- L90 placeholder substitution 機構未定義 (5/9)
- L97 "evaluation subagents" terminology + parent-model premise (5/9)

### バージョン経緯

- v0.1.0 (initial) → v0.1.1 (翻訳起因 wording 修正: Phase 7→8 ジャンプ条件 / 行番号参照の脆弱性 / retry duration 曖昧 / evals.json `expectations` → `assertions`) → v0.2.0 (sibling skill 分離 + γ/δ 共有 fix の両 plugin 同期適用) → v0.2.1 (full-test iter-2 で発見した A2/B2/D2/ζ symmetric fix)。

## 2026-05-21 (initial release)

- N 独立 subagent + reproducibility threshold (≥K/N) で CLAUDE.md 系 instruction file を多エージェント監査する初回リリース (v0.1.0)。
- agents/{auditor, false-positive-detector, default-redundancy-checker, fix-safety-checker}.md の 4 subagent + Phase 1-8 workflow を確立。

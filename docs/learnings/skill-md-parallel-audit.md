# Learnings — skill-md-parallel-audit

各セッションで得た知見を新しい順に記録。

## 2026-05-22 (full-test iter-2 verification + Phase 0/6.5 統合)

### 設計判断

- **Sibling engine sharing pattern が確立**: `agents/{auditor, false-positive-detector, fix-safety-checker}.md` を `claude-md-parallel-audit` から **byte-for-byte copy**、`skill-md-redundancy-checker.md` のみ SKILL.md 固有として新規。DRY 違反だが self-contained install を優先。3 件目の use case が出てきたら共通 backend 抽出を検討。
- **Phase 0 (skill-eval pre-audit static_check) を新設**: 3 役割 ─ hard-fail gate (構造的破綻時 audit 中止) / 構造軸の skill-eval 委譲を強化 (auditor が再 flag しない) / body 行数から N defaults を自動 suggest。
- **Phase 6.5 (post-fix static re-check) が必要**: Phase 8 の skill-eval stop criterion (`score=1.0 AND warnings=0`) は post-fix 値を要求するが、ad-hoc 再 run では trigger 曖昧 → 明示 Phase に。Phase 0 と同じコマンド shape で iteration-N に書き出す。
- **SKILL.md 固有 exclusion defaults** (Phase 1 pre-load): 公式 `subagent_type` 名 / placeholder 慣習 (`<this-skill-path>` 等) / cross-skill 情報的 pointer / frontmatter 内容 (skill-eval 所管)。
- **`skill-md-redundancy-checker` が `default-redundancy-checker` を置換**: 質問が「Claude Code defaults と被るか」(claude-md 用) ではなく「他 skill (skill-creator / skill-eval / siblings) と被るか」(SKILL.md 用) になる。

### 気付き / gotcha

- **SKILL.md 固有 exclusion defaults が機能**: iter-1 で `subagent_type: general-purpose` 等の false positive 0/9 まで抑制 (cmpa C-plan trial の 3/9 比)。auditor.md 本体は file-type agnostic で再利用可能と実証。
- **Auto-mode classifier の挙動が場所依存**: plugin source `plugins/*/skills/*/SKILL.md` → NOT protected (plugin artifact)。Installed `~/.claude/skills/*/SKILL.md` → protected (user CLAUDE.md Tier 2)。Phase 6 で location qualifier 必須、Edit 拒否時は `claude-md-parallel-audit` Phase 6b authorization template を流用。
- **Marketplace root が未収集**: L154 `glob plugins/*/skills/*/SKILL.md` は cwd = marketplace root を unstated 前提。target SKILL.md が非 marketplace 配置だと glob 空。要 fallback。

### iter-2 未解決 convergent (asymptote)

- L131 skip "4.5–6" 範囲が Phase 6.5 含むか不明 (8/9) ─ sibling は全列挙、本 skill は範囲表記
- L154 marketplace root path 未収集 (8/9)
- L194 cross-skill 依存 (claude-md-parallel-audit Phase 6b 必須) ─ sibling 未インストール時 fallback 不在 (8/9)
- L73 / L289 cost figure 不整合 (>500k vs 440k) + Phase 0/6.5 cost 抜け (6/9)
- L263 Tool Requirements "foreground + parallel within one message" 論理矛盾 (6/9)
- 構造的 asymptote として受容、無限 iter 追求しない方針。

### バージョン経緯

- v0.1.0 (initial sibling 作成) → v0.2.0 (full test iter-1 で発見した γ/δ + Phase 0 統合 + cost 較正) → v0.2.1 (iter-2 verification 後 α/γ/δ+ε/ζ/D2-analog の 5 fix + cmpa との sibling parity)。

## 2026-05-22 (initial release)

- claude-md-parallel-audit の SKILL.md target 用 sibling を新規作成 (v0.1.0)。
- C-plan trial (`skill-eval/SKILL.md` を target に N=9 走らせる) で 9/9 convergence、auditor.md の 7 軸が file-type agnostic と実証 → engine 再利用可能性を確認。

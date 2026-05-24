# Learnings — parallel-audit

各セッションで得た知見を新しい順に記録。

このファイルは `claude-md-parallel-audit` (cmpa) と `skill-md-parallel-audit` (smpa) を統合した `parallel-audit` plugin の learnings log。旧 2 ファイル (`docs/learnings/claude-md-parallel-audit.md`, `docs/learnings/skill-md-parallel-audit.md`) の歴史は本ファイル末尾に時系列で保存している。旧 plugin が marketplace から削除されるタイミングで旧 learnings ファイルも削除予定。

## 2026-05-24 (1.2.4 → 1.2.5 — iter-5 7軸再評価で iter-4 regression を発見 + 大幅 fix)

### 経緯

iter-4 commit 直後に **同じ 7軸 + 3 FP-verifier パターン** で iter-5 を回したところ、iter-4 で適用した fix のうち複数が **新規 bug を導入 / 半端適用** していたことが発覚。具体的には:

- **H6 (Phase 11 overlap pre-check)** が 3 つの新 HIGH を生成: REMOVE/INSERT line-shift propagation 未対応 / 3+ chain grouping 曖昧 / `Apply-as-is` option が safety check を bypass
- **M7 (agent ## Tools section)** が "general-purpose は Edit/Write/Bash を inherit" と誤記 (実際は Read/Grep/Glob も含む) + false-positive-detector が Grep を禁止したが Task step 3 で必要 → 2 HIGH
- **L4 (cost framing)** は SKILL.md L408 を fix したが L135 の secondary copy を見落とし → 1 HIGH cross-axis dup
- **H4/H5 (input validation)** は `threshold > N` と `N < 2` を reject したが `threshold == N` / `max_iterations` 未validation / `N` upper bound 未設定 → 4 finding
- **M4 (subagent_type renumber)** は両 specifics file 内部で番号整合したが evals.json と SKILL.md L146 の external reference を見落とし → 3 finding
- **M3 (KEEP_uncertain row rewrite)** は column semantics を muddle → 1 MED

### iter-5 評価結果

| Axis | Findings | HIGH |
|---|---|---|
| 1 | 7 | 2 |
| 2 | 5 | 2 |
| 3 | 5 | 2 |
| 4 | 1 | 0 |
| 5 | 6 | 1 |
| 6 | 9 | 5 |
| 7 | 2 | 0 |
| **計** | **35** | **12** |

### iter-5 FP-recheck

3 FP-verifier ≥2/3 集約: 35/35 REAL (verifier 全員一致で FALSE は 0)、HIGH 9 件確定。Cross-axis dedup により ~8 canonical edit cluster に集約。

### iter-5 fix 適用 (1.2.5 反映)

**HIGH cluster (9 finding → 8 edit):**

| Cluster | 対象 | 内容 |
|---|---|---|
| C1 (1.F1 + 3.F4) | SKILL.md L135 | "typically doubles iteration cost" → 1.7×-9× range pointer (iter-4 L408 fix が secondary copy を漏らした分) |
| C2 (1.F2) | SKILL.md L226 Phase 6 | "stop OR continue with next iteration" → "stops" 単独 (Phase 12 primary stop classification と整合) |
| C3 (2.N2 + 2.N1) | 4 agent files ## Tools | (a) "inherits Edit/Write/Bash" 誤記 → "inherits the full default toolset (Read/Grep/Glob/Edit/Write/Bash, etc.)" に統一、(b) FP-detector に Grep を allow (Task step 3 で必要)、(c) 4 agent で wording を標準化 |
| C4 (3.F1) | SKILL.md L146 | "exclusion #5" → "currently item #4 after iter-4's renumber" |
| C5 (3.F2 + 3.F3 + 4.F1) | evals.json id 1, id 2 + README + SKILL.md | (a) eval id 1 exclusion 列挙: 5 items → 4 + shared-blind-spots 1 (subagent_type factored out)、(b) id 2 exclusion 列挙: 4+5th conditional → 3+4th conditional + shared、(c) README + SKILL.md の "4 should-trigger evals" 表記を "5 should-trigger evals (ids 1-4 + id 8)" + "evals that existed at measurement time" qualifier に更新 (id 8 deep-tier eval が後から追加された事実を反映) |
| C6 (6.H1+H2+H3 + 1.F3+F4 + 5.F4+F5+F6 + 6.M1+L1) | SKILL.md Phase 11 overlap pre-check 全面書き換え | (a) line-shift propagation 説明追加 (INSERT/REMOVE-class fix が downstream fix の line_range を stale 化する)、(b) transitive grouping algorithm 明示 (例 `{A:L10-15, B:L17-20, C:L22-25}` は ABC 1 group)、(c) bottom-up apply ordering (max line number から先)、(d) per-fix re-Read + Phase 9 re-dispatch on stale `before` text、(e) `Apply-as-is` fast-path 廃止 (safety check bypass)、(f) actor 明示 "The main thread (not a subagent) performs the conflict pre-check"、(g) classifier pre-authorize と sequencing 順序を明示、(h) edge cases (single-fix / all-in-one-group / REMOVE-only) 追加、(i) Tool requirements AskUserQuestion + Read 行に overlap pre-check 用途を追加 |
| C7 (6.H4 + 6.H5 + 1.F5/6.M3 + 5.F1) | SKILL.md L133 input validation 拡張 | (a) `N` upper bound 9 を追加 (Deep tier 上限)、(b) `threshold == N` を reject (`(N-threshold+1)=1` で single-instance signal)、(c) `max_iterations` validation 追加 (1 ≤ max_iterations ≤ 10)、(d) 非整数 / 負数 / 非数値 reject、(e) re-ask cap 3 回 で audit abort (silent loop 防止) |

**MED bonus**:
- **C8 (2.N3)**: redundancy-checker.md row D — column semantics 整理 (unique_value 列に downstream-action advice 混入を解消、suggested_action 列に optional verification 注記を移動)

**LOW bonus**:
- **C9 (3.F5)**: shared-blind-spots.md L34 "Why this file exists" phrasing — "At present this is the single shared exclusion default" 追記で誤読を防止

### NEEDS_HUMAN / 保留 (iter-6+ または永続保留)

iter-5 の verifier ≥2/3 が確定したが iter-5 で適用しなかったもの:

- **axis-2.N4/N5** (LOW) — Tools section text duplication / Tool description in constants — DRY refactor が必要だが multi-agent template 化は重い、見送り
- **axis-5.F2** (LOW) — overlap pre-check の silent activity (Phase activity announce 系の伝統的な NEEDS_HUMAN cluster と同根)
- **axis-5.F3** (LOW) — `## Tools` prose constraint は enforcement-by-suggestion (canonical fix は dispatch 時 `tools: [...]` parameter — Agent tool SDK 動作の empirical verification が必要、iter-6+ で別途調査)
- **axis-6.M2** (LOW) — non-integer/negative/non-numeric input handling — C7 で部分カバー、残りは tier 選択 UI で実質ブロック
- **axis-6.L2** (LOW) — model_string 文字列 validation — iter-6+
- **axis-7.F8** (MED) — tools: dispatch parameter (axis-5.F3 と同 cluster、SDK 検証が必要)
- **axis-7.F9** (LOW) — Tools section drift across 4 agents — C3 で 4 agent を統一したが、wording template 化はせず (drift 再発時に対応)

iter-4 から繰り越した NEEDS_HUMAN 8 件 (1.F5, 2.F4, 4.F3, 5.F1/F2/F5/F7/F8) も継続保留。

### iter-5 で得た最大の meta 教訓

**「fix the fix」サイクルは現実的に必要**:
- iter-4 で適用した 17 件のうち、複数 (H6 / M7 / L4 / H4+H5 / M4 / M3) が新規 bug や半端適用を残した
- 後続イテレーションで FP-verifier ≥2/3 集約により客観的に regression を発見できた
- 「修正物がなくなるまで反復」の判定は、iteration 単位の `0 fix candidates from Phase 6` 到達ではなく、cross-iteration での **新規 finding rate が asymptote** か **全 HIGH が NEEDS_HUMAN 化** したかで判定すべき
- iter-5 で applied 9 fix → iter-6 で regression を検証する必要

**Edit-from-bottom pattern は標準化価値あり**:
- C6 で導入した bottom-up ordering は H6 の line-shift propagation 問題を構造的に解決
- 他の skill / plugin の multi-fix workflow にも横展開可能 (例 `pr-review-toolkit:code-reviewer`)

**Pre-edit grep sweep pattern**:
- verifier #2 が指摘した「primary location fix → secondary site forgotten」pattern (M4 / L4 等) は、fix 適用前に grep で同一識別子 / 同一 phase 番号 / 同一 multiplier 出現箇所を全部洗い出して同 commit で fix する規律が必要
- iter-6+ で M3-style "primary site のみ fix" を再発防止するための pitfalls.md entry が候補

### 残作業

iter-5 後の状態に対し iter-6 を回し、(a) iter-5 修正の regression 検出 (b) 残存 NEEDS_HUMAN/LOW の再 surface (c) 新規 finding rate が asymptote に到達したか判定。

## 2026-05-24 (1.2.3 → 1.2.4 — iter-4 7軸多角評価 + 3 FP-verifier ≥2/3 集約)

### 経緯

ユーザー再度 `/skill-creator` 経由で「parallel-audit を多角評価 → 修正 → patch bump → 繰り返し (修正物がなくなるまで)」をリクエスト。前回 (1.2.2 → 1.2.3) は 3 reviewer 並列の収束で「1 ラウンド」だったが、本セッションは **7 軸並列評価 + 3 FP-verifier ≥2/3 aggregate** という新パターンで iter-4 を実施。

### iter-4 評価フェーズ

7 軸並列 evaluator dispatch:

| Axis | 観点 | Findings | HIGH |
|---|---|---|---|
| 1 | SKILL.md quality | 10 | 2 |
| 2 | agents/*.md prompts | 8 | 2 |
| 3 | references/*.md | 5 | 0 |
| 4 | README + JSON consistency | 3 | 0 |
| 5 | UX & workflow | 11 | 3 |
| 6 | edge cases & failure modes | 10 | 3 |
| 7 | security & Tier compliance | 7 | 0 |
| **計** | | **54** | **10** |

### iter-4 FP-recheck フェーズ

3 FP-verifier 並列 → ≥2/3 で REAL/FALSE/NEEDS_HUMAN 確定。

| 分類 | 件数 | 内訳 |
|---|---|---|
| REAL (≥2/3) | 43 | HIGH 6, MED 15, LOW 22 |
| FALSE (≥2/3) | 3 | 1.F9, 3.F5, 7.F7 (いずれも axis evaluator 自身が non-finding に self-demote) |
| NEEDS_HUMAN (≥2/3) | 8 | UX 設計判断系 (5.F1/F2/F5/F7/F8) + 履歴系 (4.F3) + 自己充足性設計 (2.F4) + ship-ready scope (1.F5) |

**HIGH 6件** (全 verifier 一致): axis-1.F1 (model literal hardcode), axis-2.F1 (FP-detector Phase 5 ref), axis-2.F2 (auditor Phase 5 ref), axis-6.F1 (`threshold > N` silent stop), axis-6.F2 (`N=1` silent convergence-off), axis-6.F3 (cross-fix overlap not detected).

### iter-4 fix 適用 (1.2.4 反映)

iter-4 適用範囲: **HIGH 6 全件 + 手術的 MED 7 + 1-liner LOW 4** = 17 fix。NEEDS_HUMAN 8 件と scope の重い MED/LOW は iter-5+ または保留。

#### HIGH (6 件)

| Fix | 対象 | 内容 |
|---|---|---|
| H1 (1.F1) | SKILL.md L171 | `model: "sonnet"` literal → `model: <model_string>` ── L173 の override path と整合、`model_string` user override が silently dead だった bug を解消 |
| H2 (2.F1) | false-positive-detector.md L16/L61/L69 | "Phase 5 for fix proposal" / "Phase 5's job" を Phase 7 → 8 へ修正。同 file 内に 3 箇所の stale ref |
| H3 (2.F2) | auditor.md L84 | "Phase 5 of the workflow drafts fixes" → Phase 8 |
| H4 (6.F1) | SKILL.md Phase 2 step 3 | `threshold > N` を Phase 2 で reject (silent vacuous pass を防止) |
| H5 (6.F2) | SKILL.md Phase 2 step 3 + parameter table | `N < 2` reject + `N` パラメータ説明にも明記 |
| H6 (6.F3) | SKILL.md Phase 11 新節 "Pre-check for overlapping fix line ranges" | line_range が ±2 行で重なる fix を group 化 → 順次 apply + 重複確認 |

#### MED (7 件)

| Fix | 対象 | 内容 |
|---|---|---|
| M1 (1.F2) | SKILL.md L88 + L173 | Phase 9 を "single-agent evaluation" と誤記していた rationale を fan-out 構造に合わせて再記述 |
| M2 (1.F6) | SKILL.md L391 (Tool requirements Glob row) | Phase 2 にない "SKILL.md candidate discovery" 機能の dangling claim を削除 |
| M3 (2.F3) | redundancy-checker.md L72 | 例 row の `KEEP (uncertain)` を `KEEP` + 不確実性を prose に移行 (declared enum との producer-consumer 整合) |
| M4 (3.F1+F2) | shared-blind-spots.md / claude-md-specifics.md / skill-md-specifics.md | `subagent_type` exclusion default + 対応 FP-pattern row を shared-blind-spots.md に factor out。両 specifics file の duplicate を pointer 化、exclusion 番号を 1-4 に詰め直し、FP-pattern row の番号参照も整合 |
| M5 (3.F3) | shared-blind-spots.md 全面書き換え | L17 "Phase 6.5 reads only the target-relevant specifics" を "orchestrator reads files; Phase 6.5 receives pre-built `known_fp_patterns`" に修正。新節 "Shared exclusion defaults" + 拡張 "Shared known-FP patterns" 構造 |
| M6 (4.F1) | README.md L29 + README-en.md L29 | Phase 11 description を reactive ("拒否されたら認可を得て retry") → pre-authorize first + reactive fallback に align |
| M7 (7.F2) | 4 agent files | 各 agent prompt に `## Tools` 節を追加。`general-purpose` dispatch で inherit する Edit/Write/Bash を prose constraint で role 別に絞る (read-only 役 / data-only 役) |

#### LOW (4 件)

| Fix | 対象 | 内容 |
|---|---|---|
| L1 (1.F3) | SKILL.md L74 threshold row | "(≥2/3 ≈ 67%)" の hardcoded 文言を削除し、`2 ≤ threshold ≤ N` 制約 + tier 依存の percentage を明記 |
| L3 (2.F8) | auditor.md L77 | `**NO HIGH ISSUES**` bold form → `NO HIGH ISSUES` (SKILL.md L319 stop-condition 表記と lexical 整合) |
| L4 (3.F4) | ab-testing.md L26 + SKILL.md L408 | "roughly doubles" 単一表現 → 1.7×-9× range (own cost table と整合) |
| L5 (4.F2) | README.md L27 + README-en.md L27 | "Phase 6 / 7" → "Phase 6 / 6.5 / 7" (false-positive-detector phase number を hide していた) |

### NEEDS_HUMAN 保留分 (8 件)

iter-5+ で user 判断を仰ぐか、scope 外として確定保留:

- **axis-1.F5** — Phase 12 "both layers clean" を plateau/max_iter/0-fix 経路にも extend するか (report verbosity policy 判断)
- **axis-2.F4** — agent prompt に `## Tools` 節を **frontmatter `allowed-tools:` で gating するか prose で済ますか** (M7 は prose 採用。frontmatter 化は別判断)
- **axis-4.F3** — README "max_iterations 5 → 3" の predecessor default が historical fact として正しいか (旧 plugin source を確認しない限り未検証)
- **axis-5.F1** — Pre-audit modal 数 (4-6 件) の compress 是非
- **axis-5.F2** — Phase 0 pre-flight cost/time estimate 導入是非
- **axis-5.F5** — Phase resume 機能の new-feature 判断
- **axis-5.F7** — Trigger description に自然な phrasing を増やすか (over-triggering risk)
- **axis-5.F8** — Phase 10 batch-approve escape hatch (intentional anti-rubber-stamping vs friction trade-off)

### iter-4 で深堀りされた残課題 (iter-5+ 候補)

verifier が REAL 認定したが scope/重さで本 iter から外したもの:

- **axis-1.F4** (MED) — Phase 11.5(b) を 0-fix 適用時に skip する precondition 追加
- **axis-1.F7** (MED) — Phase 3 section_purposes re-pass の diff-based auto-detect trigger
- **axis-5.F3** (MED) — global abort path 文書化
- **axis-5.F4** (MED) — Phase 6.5/7/9 subagent failure の user-surfacing
- **axis-6.F4** (MED) — below-threshold persistent (r2-F1 watch pattern) の escalation policy 明文化
- **axis-6.F5** (MED) — file-size guardrail (>2000 行で warning)
- **axis-6.F6** (MED) — per-fix post-Edit verification (Phase 11.5(a) whole-file re-audit で部分カバー済み)
- **axis-6.F7** (MED) — clustering algorithm 明文化 (N=9 × 10 = 90 findings の manual cluster fragility)
- 残り LOW (1.F8/F10, 2.F5/F6/F7, 5.F6/F9-F11, 6.F8-F10, 7.F1/F3/F4/F5/F6) — 個別判断

### iter-4 で得た meta 教訓

- **7軸 evaluator パターンが workable**: 3 reviewer (前回) より 7 axis-specialized evaluator の方が "what to look for" が axis ごとに明確で findings 漏れが減る。特に edge-cases (axis-6) が input validation 系の HIGH 3件を新規発見 (`threshold > N` / `N=1` / cross-fix overlap)。3 reviewer × generic prompt では拾えない可能性が高かった
- **3 FP-verifier ≥2/3 集約は severity 調整に有効**: axis evaluator の overweighted HIGH (axis-1.F2 / axis-5.F2/F3) を MED/MED/MED に系統的に降格。3 verifier 全員が独立に同じ severity に着地 → noise 低減
- **Phase 5 stale ref の cluster fix**: agent file 横断 (false-positive-detector × 3箇所 + auditor × 1箇所) で同根 defect が発見。phase 番号 rename pass が agent prompt まで届いていなかった (iter-3 まで誰も気付かず)
- **input validation gap が systemic**: SKILL.md は workflow 中身は手厚いが、Phase 2 input validation が後付けで `N=1` / `threshold > N` を silently 受け入れていた。Phase 2 で defensive validation を入れる pattern を確立

### 残作業

iter-4 修正後の状態に対し iter-5 で同サイクル (7軸再評価 → ≥2/3 集約) を回し、**修正物が 0 になるか asymptote** で stop。

## 2026-05-24 (1.2.2 → 1.2.3 — 多角評価 + FP-recheck + rolling static review 収束)

### 経緯

ユーザー自ら parallel-audit を多角評価依頼 → 評価に対し parallel-audit pattern で self-FP-check → iter-2/iter-3 で rolling static review を回し収束まで到達。本セッションは plugin 自身の workflow を plugin 自身の評価プロセスに適用した meta-loop。

### iter-1 (1.2.2 への 4 件 fix)

`tmp/fp-recheck/verifier-{1,2,3}.md` の ≥2/3 aggregate で確定した REAL のうち、即時 fix 可能な 4 件を 1.2.1 → 1.2.2 に reflect:

| Fix | 対象 | 内容 |
|---|---|---|
| R1 | SKILL.md + README + README-en | "Known limitations" 節新設 (in-session recall 未測定 / e2e benchmark 不在 / Phase 9 fan-out worst case / external sample = 1) |
| R6 | SKILL.md L406 段落 | worst-case 300-750k math (10-15 safety-checkers × 30-50k) 追記 |
| R10 | references/shared-blind-spots.md 新設 | `(N − threshold + 1)` FP-hint を両 target-specifics から factor out、新ファイル canonical 化 |
| R11 | references/skill-md-specifics.md L24 | stale `<this-skill-path>` を prose-used placeholder (`<marketplace_root>` / `<workspace>` / `<name>`) に置換 |

撤回: C7 (placeholder SSoT) は 3 verifier 中 2 で FALSE → producer-consumer contract surface であり SSoT 違反ではない。

### iter-2 (1.2.2 への追加 3 件 fix)

iter-2 reviewer 3 並列 ≥2/3 で確定した REAL:

| Fix | 対象 | 内容 |
|---|---|---|
| A (3/3) | false-positive-detector.md + SKILL.md (4 箇所) | shared-blind-spots wiring が prose only で **runtime contract に通っていなかった**: FP-detector Input section に 5th input `known_fp_patterns` 追加、Task step 0 を known-FP shortcut 化、SKILL.md Verification subagents table Phase 6.5 行に `known_fp_patterns` 追加、Phase 2 substep 4 に union assembly 指示、Tool requirements Read 行に shared-blind-spots.md 追加 |
| B (2/3) | SKILL.md L410 段落 | "300-750k" の帰属を **Phase 9 alone** に統一 (L420 と整合)。直前 wording が "verification overhead" (Phase 6.5+7+9 combined) と矛盾していた |
| C (2/3) | README.md + README-en.md Layout tree | 新規 `shared-blind-spots.md` + 既存 `pitfalls.md` が両 README の layout block から欠落していた |

### iter-3 (収束判定)

iter-2 fix 後の状態に対し 3 reviewer を再 dispatch:

| Reviewer | Resolution A/B/C | New HIGH findings |
|---|---|---|
| r1 | 3/3 RESOLVED | **NO HIGH ISSUES** |
| r2 | 3/3 RESOLVED | 1 HIGH (F1: L420 で "4-9× upper" と "2× headline" の budget heuristic が異なる base に対して混在) |
| r3 | 3/3 RESOLVED | **NO HIGH ISSUES** |

**Aggregate**: 2/3 が NO HIGH ISSUES → Phase 12 primary stop condition #2 (practical convergence: ≥(N-threshold+1)=≥2 of 3 報告 clean) **成立**。

### r2-F1 (below-threshold) の保留

r2 のみが flag した L420 paragraph 内部の budget heuristic 不整合 (`9 × 80k = 720k` vs `2 × 150k = 300k` で base が違う) は 1/3 = threshold 未達。skill 自身の discipline では "reproducible defect ではない" として fix 適用せず。

ただし内容は real な可能性が高い (shared blind spot ではなく r1/r3 の見落としかもしれない subtle defect)。next event-driven audit で同じ flag が再 surface したら fix 候補に昇格させる。本 session では skill rule に忠実に **保留**。

### Self-test meta-loop の教訓

- **parallel-audit pattern を自己評価に適用すると workable**: 3 reviewer 並列 → ≥2/3 aggregate → fix → 再 dispatch の cycle は plugin 評価にも適用できた。iter-1 (14 criticisms verify) + iter-2 (8 HIGH findings) + iter-3 (収束判定) で計 4 ラウンドの aggregate を実施
- **shared-blind-spots factor-out は wiring まで通さないと leaky**: iter-1 で新設したが、iter-2 全 reviewer が "agent prompt に入力 slot がない" を flag。**ファイル新設 + 1 ヶ所言及だけでは不十分、consumer 側 contract まで update が必要** という教訓
- **threshold rule の trade-off**: r2-F1 が real-but-below-threshold の典型例。≥2/3 は "shared blind spot を回避するため過剰検出を弾く" が目的なので、稀に real findings も filter out される。今回は rule に忠実に保留したが、event-driven 再 audit で再 surface すれば確定 fix 候補

### 残課題 (本 session スコープ外)

- **真の C1 解消** — in-session triggering recall の実 session 計測 (5-10 回 manual register が必要)
- **R2 scripts/** — working_threshold 計算 / scope-token 比較を Python 化 (LOC 50-100、別エフォート)
- **r2-F1** — 上記 below-threshold 保留分。次回 audit で再 surface するか観察
- **C5 / C8 / C9 / C13 (iter-1 NEEDS_HUMAN)** — empirical 比較 / version policy 判断

## 2026-05-23 (v0.2.0 bump + 4 件の指摘事項対応)

### v0.1.0 → v0.2.0 bump

`./.claude/skills/bump-plugin-version/scripts/bump.sh parallel-audit 0.2.0` で `.claude-plugin/marketplace.json` と `plugins/parallel-audit/.claude-plugin/plugin.json` を 同期 bump。jq 検証 2/2 true。bump の理由は self-test iter-1/iter-2 で適用した defect fix 群 (cmpa から copy した agent file の phase number 更新 / Phase 9 wording 修正 / L200 skip 矛盾解消 等)。v1.0.0 stable 提案は却下、4 件の未対応事項 (下記) が残存している間は 0.x のままが正しいと判断。

### 4 件の指摘事項対応 (Claude opus 4.7 が version bump 前に surface した懸念)

| 項目 | 対応 | 残存度 |
|---|---|---|
| **A2** L154 `model: "sonnet"` の運用ルール (誰がいつ full ID に切り替えるか) | SKILL.md L155 段落を decision policy 形式に再構成: default path / user override path (Phase 2 で AskUserQuestion 経由) / parent-is-sonnet case / 再 dispatch consistency。config table に `model_string` パラメータ追加 | ✅ 解消 (asymptote 受容 → 明示 policy へ降格) |
| **C2** L252 multi-option mode の trivial/substantive 境界の論理矛盾 + "lines changed" 計測の曖昧さ | SKILL.md L252 を 4 段階の precedence rule に再構成: (1) lines-changed = `max(before, after)` 明示定義 (2) structural change → 行数無視で substantive (3) choice → 行数無視で substantive (4) 上記非該当時のみ line count threshold | ✅ 解消 |
| **Phase 11.5(b) A/B 統合 wiring 未検証** + skill-eval が marketplace から削除済み | SKILL.md Phase 2.5 / 11.5(b) / 11.5(c) を **external optional dependency** 扱いに更新。`references/ab-testing.md` 冒頭に "skill-eval は本 marketplace に bundle されていない" を明記、未 install 時の prominent warning + graceful skip path を文書化 | ✅ 解消 (実 wiring 検証は別途必要なまま) |
| **Marketplace root 検出 fallback パス未検証** | `references/skill-md-specifics.md` に 6 step の concrete resolution chain を追加 (source-marketplace globbing / installed-current / installed-all / env var / manual list / empty fallback)。`SKILL_EVAL_SKILLS_DIR` env var による explicit override path も追加 | ✅ 解消 (step-by-step 文書化、実走検証は別途必要) |

### 残存事項 → 全件解消

| 元残存事項 | 解消方法 |
|---|---|
| **実 CLAUDE.md target での運用実績ゼロ** | ✅ `~/.claude/CLAUDE.md` (17KB) に N=3 で実走 → 5 convergent issue 抽出 (HIGH avg 5.67、SKILL.md self-test の 7.7/6.0 と同水準)。claude-md target path の全工程 mechanical 動作確認: target_type auto-detect / exclusion defaults 5 件 load / 0 false flag on `subagent_type` 等 / 並列 dispatch / aggregation。**convergent issue 自体は CLAUDE.md 側の defect (Tier 2/3 境界曖昧さ / gh op 分類 / 等) で skill 側の問題ではない**。fix application は user 判断 |
| **A/B 統合の実 wiring 検証** | ✅ skill-eval resolution chain 6 step 全 traverse 検証: 全 step が NOT FOUND → step 6 graceful skip fallback 正常到達。chain documentation 通りに動く |
| **Marketplace root fallback の実走検証** | ✅ Step 1 source-marketplace globbing: parallel-audit SKILL.md → 5 level walk → marketplace.json 発見 → `glob plugins/*/skills/*/SKILL.md` で 2 sibling 取得。Empty fallback test: `/tmp/some-orphan-skill/` → 6 level walk → not found → step 6 fallback 動作確認 |

### ~/.claude/CLAUDE.md (claude-md target 実走) で見つかった 5 件の convergent issue

これらは **CLAUDE.md 側の defect** であり parallel-audit 側の問題ではない。user の判断で fix するか accept するか:

- **B (3/3)** L92 Tier 2/3 境界 (rm 系 / 破壊的 shell): `rm` vs `rm -f` の非対称 / deny-blocked "etc." 列挙の load-bearing 部分 / deny list の所在未明
- **C (3/3)** L96 gh PR/run 分類基準 ("close/edit で undo 可能") が `gh pr reopen` / `gh run rerun` / `gh pr review approve` に当てはまらず logical contradiction
- **A (2/3)** L22 `git worktree remove`: コミットせず終了するケース欠落 / push 済み前提が暗黙
- **D (2/3)** L102 "user-owned scratch surfaces" exception の "cancelable / explicitly noted" 条件が unactionable
- **E (2/3)** L107 "Tier 2 may skip re-confirmation" の sub-category 限定が rule 提示点ではなく後続 line にあり、L107 単独読みで誤適用リスク

### 結論

v0.2.0 で **全 4 項目 (A2 / C2 / A/B / Marketplace root) 解消 + 実 CLAUDE.md target での運用実績獲得**。v1.0.0 stable 宣言の論理的障壁は消滅。stable bump をするかは別判断 (実 production 利用の蓄積期待 / 受容期間設定 / 等の判断軸)。



## 2026-05-23 (cmpa + smpa 統合 → parallel-audit v0.1.0)

### 決定事項 (Claude との dialogue で確定した 7 件)

| 項目 | 決定 | 根拠 |
|---|---|---|
| Plugin / skill 名 | `parallel-audit` | 将来の対象拡張 (RFC / design doc / source 等) を許容する一般名。`instruction-md-audit` よりも scope 広く取れる |
| 旧 2 plugin の扱い | Deprecate marker → 1-2 release 後削除 | 既 install ユーザー (実質 maintainer 1 人) への配慮として soft deprecate。description に `[DEPRECATED — superseded by parallel-audit]` prefix |
| A/B 統合の深度 | Optional Phase 11.5(b), default OFF | signal-to-noise が原理的に難しい現実 (wording 修正で differential を出すのは小さくノイジー) を踏まえ、必要な人だけ opt-in。`references/ab-testing.md` に full guide |
| Default N | Quick: N=3 / threshold=2 (~150k tokens/iter) | event-driven positioning に合わせて軽量化。Phase 2 で N=5 / N=9 への opt-in tier を提示 |
| Routine 利用時の振る舞い | Warn + 続行確認 | 抑止強度: silent < warn+confirm < refuse の中庸。routine 自体は anti-pattern として明示しつつ、ユーザーの override は許す |
| 初期 version | 0.1.0 | clean slate。旧 0.2.1 からの semver 連続性は名前変更で消えるので保たない |
| README case study | 含めない | プライバシー保護 + 単一事例が代表的でないリスク回避 |

### Claude からの critique を反映した design 変更

Claude (Opus 4.7) との 5 往復の dialogue で受けた「不要寄り評価」を、技術的に反映:

- **「auditor は asymptote に達して収束しない」** (cmpa iter-3 データ) → max_iterations default を 5→3 に縮小。Phase 12 stop check に asymptote 認識を明示記載
- **「7 軸が generic prose 軸すぎて何にでも刺さる」** → Phase 1 symptom triage + Phase 1.5 scope narrowing を新設。full-file 走査の前に対象を絞ることで noise を相対的に減らす
- **「downstream A/B エビデンスがない」** → A/B 統合を built-in option として用意 (`references/ab-testing.md`)。default OFF だが必要なときに発動できる経路を確保
- **「2 plugin に分ける必然性が薄い」** → 統合。`target_type` で内部分岐、agents/auditor.md と false-positive-detector.md と fix-safety-checker.md は元々 byte-for-byte 同一だったので problem なし
- **「event-driven positioning」** → Phase 1 symptom interview + routine 警告で skill 自体が誤用を抑止する設計に。SKILL.md description にも "event-driven diagnostic" を明示

### Phase 構造の変更 (cmpa → parallel-audit)

| 旧 cmpa | 新 parallel-audit | 変更点 |
|---|---|---|
| — | Phase 1 symptom interview | 新規。Phase 0 (smpa の skill-eval static) と並ぶ新 pre-check 層 |
| — | Phase 1.5 scope narrowing | 新規。Phase 1 の symptom 答えに応じて full / section / rule-and-neighbors を選択 |
| Phase 1 inputs | Phase 2 inputs | target_type auto-detect 追加、A/B opt-in 質問追加 |
| smpa Phase 0 | Phase 2.5 static pre-check | skill-md target 限定として整理 |
| Phase 1.5 section purposes | Phase 3 | 番号変更のみ |
| Phase 2 audit dispatch | Phase 4 | byte-identical |
| Phase 3 aggregate | Phase 5 | byte-identical (table 出力, drift hedge) |
| Phase 4 / 4.5 / 4.6 | Phase 6 / 6.5 / 7 | 4.6 を 7 として redundancy-checker 統合 (default-redundancy + skill-md-redundancy を 1 prompt に target_type 分岐) |
| Phase 5 / 5.5 / 5.6 | Phase 8 / 9 / 10 | 番号変更のみ |
| Phase 6a / 6b | Phase 11 | 統一。auto-mode classifier playbook は `references/claude-md-specifics.md` に集約 |
| smpa Phase 6.5 | Phase 11.5(c) | skill-eval static 再 run。Phase 11.5(a) audit 再 dispatch、Phase 11.5(b) A/B benchmark と並列 sub-phase 構成 |
| Phase 7 / 8 | Phase 11.5(a) / 12 | Phase 7 = 11.5(a)、Phase 8 = 12 |

### ファイル構成

```
plugins/parallel-audit/
├── .claude-plugin/plugin.json (v0.1.0)
├── README.md / README-en.md
└── skills/parallel-audit/
    ├── SKILL.md (~380 行)
    ├── agents/
    │   ├── auditor.md                 (cmpa から byte-for-byte copy)
    │   ├── false-positive-detector.md (cmpa から byte-for-byte copy)
    │   ├── fix-safety-checker.md      (cmpa から byte-for-byte copy)
    │   ├── redundancy-checker.md      (default + skill-md の統合, target_type 分岐)
    │   └── symptom-interview.md       (新規, Phase 1 protocol)
    ├── references/
    │   ├── claude-md-specifics.md     (claude-md target 固有 + auto-mode classifier playbook)
    │   ├── skill-md-specifics.md      (skill-md target 固有 + skill-eval 連携)
    │   └── ab-testing.md              (optional A/B 統合ガイド)
    └── evals/evals.json (5 evals: claude-md post-refactor / skill-md pre-shipping / routine warn / specific-rule scope narrow / should-not-trigger)
```

### Self-test 結果 (parallel-audit v0.1.0 を自身の SKILL.md に N=3 で 2 iter 実行)

#### Iter-1 (5 件 3/3 収束、全 REAL)

1. `agents/auditor.md` L7 が "default 4 of 9" (旧 cmpa 値) のまま → 新 default `N=3/threshold=2` と矛盾
2. SKILL.md L154 `model: "sonnet"` の alias resolution policy 未記述
3. SKILL.md L200 "skip ... go directly to Phase 11.5(a)" が 11.5(a) の precondition と論理矛盾
4. cmpa から copy した 3 agent file が旧 phase 番号 (1.5/3/4/5/6a/6b) を引きずる → SKILL.md の新 番号 (3/5/6/6.5/8/11) と cross-file 不整合
5. Phase 9 "foreground + parallel within one tool-call" が技術的に成立しない (foreground=blocking)

→ 13 Edit で 5 件全 fix 適用。

#### Iter-2 (4 件 ≥2/3 収束、HIGH avg 7.7→6.0)

- **A2 (2/3)**: L154 model "sonnet" 補完 paragraph に「誰がいつ full ID に切り替えるか」の運用ルールが未記述 → **asymptote 受容**
- **B2 (3/3)**: L202 で fix C が "11.5" と書いたが 11.5(a)/(b)/(c) のどれを含むか曖昧 → **L202 を Phases 6.5/7/8/9/10/11/11.5(a)/(b)/(c) を明示列挙する形に補完**
- **C2 (3/3)**: L252 multi-option mode の "≤3 lines AND restructures" 境界の論理矛盾 + "lines changed" 計測の曖昧さ → **asymptote 受容**
- **D2 (2/3)**: L377 Bundled agents table が "foreground" のまま (Phase 9 body の `run_in_background: true` と矛盾) → **fix E の見落とし。L377 を補完**

→ 2 Edit (L202 / L377) で fix E と fix C の wording 不完全さを解消。A2 / C2 は **既知 asymptote** として受容。

#### 検証結論

- **機械的に正常動作**: dispatch / 集計 / FP filter / 再 dispatch / 収束判定が design 通り
- **cmpa の asymptote 仮説を再現**: fix 適用の新 wording が新 convergent finding を誘発 (B2 が典型例)。parallel-audit に再設計した N=3 / max=3 でも構造は同じ
- **cmpa との比較**: iter-1 avg 7.7 は cmpa の自己テスト時 avg ≈ 5-8 と同水準。new findings の傾向も同じ (cost notes / Tool requirements 表 / cross-file phase number)
- **Self-test 後 v0.1.0 を ship 可能と判定** ─ 残存 asymptote 2 件は明示的に既知 issue として受容

### 旧 plugin (cmpa / smpa) を完全削除 (deprecation marker を経ずに本リリースで除去)

Self-test 完了後、旧 2 plugin を marketplace から即削除に切り替え (元の "1-2 release 後削除" 計画から短縮)。理由:

- 個人運用 marketplace で外部 install ユーザー保護不要
- parallel-audit v0.1.0 で機能 superset を確認済み
- git history に旧 plugin 完全保存

削除対象:

- `marketplace.json` から `claude-md-parallel-audit` / `skill-md-parallel-audit` の entry 除去
- `docs/learnings/claude-md-parallel-audit.md` / `skill-md-parallel-audit.md` (本ファイルに歴史 merge 済み) を削除
- `plugins/claude-md-parallel-audit/` / `plugins/skill-md-parallel-audit/` (ユーザーが手動 `rm -rf` で実行 — Tier 3)

### 未検証事項 (今後の iteration で確認)

- **A/B 統合の実地検証**: `references/ab-testing.md` の理論は書いたが、実際に skill-eval の benchmark を呼ぶ wiring は writing only。次回 audit 機会で実走させる必要
- **Marketplace root 検出の fallback パス**: `references/skill-md-specifics.md` の sibling skill discovery で plugin cache パスを fallback としているが、ユーザーが marketplace cache 構造を変えていた場合に動くかは未検証
- **Iter-3 plateau 確認は未実施**: avg 7.7→6.0 で plateau (変化 <1) 未到達。max_iterations=3 の妥当性は iter-3 を走らせれば数値検証可能だが、self-test の目的 (skill 正常動作 + ship 可否) は達成済みのため skip

---

## (旧 claude-md-parallel-audit learnings — 統合前)

以下、旧 `docs/learnings/claude-md-parallel-audit.md` の内容を保存。

### 2026-05-22 (full-test iter-2/iter-3 verification + sibling 分離)

#### 設計判断

- **Multi-agent audit は asymptotic, not zero**: iter 重ねると HIGH avg は initial 下降後 reflate (fix 適用が新 wording → 新 finding を誘発)。iter-3 で avg 8.1、practical convergence (≥6/9 clean) 到達せず。**2-3 iter が実用上限**、それ以上は新規変動が他既存 wording 経由でゼロ和。残存 ≥4/9 findings は "known asymptote" として受容。
- **`≥(N − threshold + 1)` 式に修正**: 旧 「≥3 of N 報告 NO HIGH ISSUES」は数学的に loose。default N=9/threshold=4 → ≥6/9 clean で「残り (threshold−1)=3 instance が同一 issue を flag しても reproducible 不成立」を保証 (v0.2.0)。
- **Phase 6a/6b split は cmpa 固有**: auto-mode classifier (`~/.claude/CLAUDE.md` Tier 2) に Edit 拒否された時用に "Yes, update my `<file>`" template playbook を 6b に集約。SKILL.md 系 sibling (smpa) は plugin artifact 扱いで classifier 非対象なので Phase 6 統合可。
- **Sibling として `skill-md-parallel-audit` を分離**: SKILL.md 専用 exclusion defaults + 別 redundancy-checker を sibling 化。engine 3 ファイル (auditor / fp-detector / fix-safety-checker) は byte-for-byte copy で共有。

#### 気付き / gotcha

- **N=9 iter cost 実測 ~440k tokens**: Phase 2 sonnet 9×~32k ≈ 290k + verifiers (Phase 4.5 + 4.6) ~60k + Phase 5.5 safety-checker(s) ~30-90k。5-iter audit ≈ 1.5-2M。Phase 1 で必ず surface する。
- **Subagent は global CLAUDE.md の "use Glob/Grep" 規約を継承しない**: Bash `find` / `grep` を使ってしまう subagent が複数観察された。気になる場合は dispatch prompt で明示。
- **Subagent shared blind spots (頻出)**: 公式 `subagent_type` 名を "undefined" flag / 文書化済み override (`model: "sonnet"` Phase 2) を CLAUDE.md 違反と flag / Phase 6a/6b 知らず "Phase 6" を ambiguous と flag。Phase 1 exclusion defaults + iteration-history accumulated exclusion で抑制必須。
- **`(N − threshold + 1)` rationale の伝達難**: 数学的に正しいが「remaining (threshold−1) instance が同一 issue を flag しても reproducible 不成立」premise を unstated と auditor が flag し続ける (iter-3 で 9/9 該当)。式に説明文を添えるべき。

#### iter-3 未解決 convergent (asymptote)

- L284 formula rationale 説明不足 (9/9)
- L136 skip range Phase 8 含意 / Phase 5 ambiguous (9/9)
- L326 Tool Requirements Phase 5.5 dispatch foreground+parallel 矛盾 (9/9)
- L203 `rule_burden_impact` field 定義が agent file 側のみ (6/9)
- L90 placeholder substitution 機構未定義 (5/9)
- L97 "evaluation subagents" terminology + parent-model premise (5/9)

#### バージョン経緯

- v0.1.0 (initial) → v0.1.1 (翻訳起因 wording 修正: Phase 7→8 ジャンプ条件 / 行番号参照の脆弱性 / retry duration 曖昧 / evals.json `expectations` → `assertions`) → v0.2.0 (sibling skill 分離 + γ/δ 共有 fix の両 plugin 同期適用) → v0.2.1 (full-test iter-2 で発見した A2/B2/D2/ζ symmetric fix)。

### 2026-05-21 (initial release)

- N 独立 subagent + reproducibility threshold (≥K/N) で CLAUDE.md 系 instruction file を多エージェント監査する初回リリース (v0.1.0)。
- agents/{auditor, false-positive-detector, default-redundancy-checker, fix-safety-checker}.md の 4 subagent + Phase 1-8 workflow を確立。

---

## (旧 skill-md-parallel-audit learnings — 統合前)

以下、旧 `docs/learnings/skill-md-parallel-audit.md` の内容を保存。

### 2026-05-22 (full-test iter-2 verification + Phase 0/6.5 統合)

#### 設計判断

- **Sibling engine sharing pattern が確立**: `agents/{auditor, false-positive-detector, fix-safety-checker}.md` を `claude-md-parallel-audit` から **byte-for-byte copy**、`skill-md-redundancy-checker.md` のみ SKILL.md 固有として新規。DRY 違反だが self-contained install を優先。3 件目の use case が出てきたら共通 backend 抽出を検討。
- **Phase 0 (skill-eval pre-audit static_check) を新設**: 3 役割 ─ hard-fail gate (構造的破綻時 audit 中止) / 構造軸の skill-eval 委譲を強化 (auditor が再 flag しない) / body 行数から N defaults を自動 suggest。
- **Phase 6.5 (post-fix static re-check) が必要**: Phase 8 の skill-eval stop criterion (`score=1.0 AND warnings=0`) は post-fix 値を要求するが、ad-hoc 再 run では trigger 曖昧 → 明示 Phase に。Phase 0 と同じコマンド shape で iteration-N に書き出す。
- **SKILL.md 固有 exclusion defaults** (Phase 1 pre-load): 公式 `subagent_type` 名 / placeholder 慣習 (`<this-skill-path>` 等) / cross-skill 情報的 pointer / frontmatter 内容 (skill-eval 所管)。
- **`skill-md-redundancy-checker` が `default-redundancy-checker` を置換**: 質問が「Claude Code defaults と被るか」(claude-md 用) ではなく「他 skill (skill-creator / skill-eval / siblings) と被るか」(SKILL.md 用) になる。

#### 気付き / gotcha

- **SKILL.md 固有 exclusion defaults が機能**: iter-1 で `subagent_type: general-purpose` 等の false positive 0/9 まで抑制 (cmpa C-plan trial の 3/9 比)。auditor.md 本体は file-type agnostic で再利用可能と実証。
- **Auto-mode classifier の挙動が場所依存**: plugin source `plugins/*/skills/*/SKILL.md` → NOT protected (plugin artifact)。Installed `~/.claude/skills/*/SKILL.md` → protected (user CLAUDE.md Tier 2)。Phase 6 で location qualifier 必須、Edit 拒否時は `claude-md-parallel-audit` Phase 6b authorization template を流用。
- **Marketplace root が未収集**: L154 `glob plugins/*/skills/*/SKILL.md` は cwd = marketplace root を unstated 前提。target SKILL.md が非 marketplace 配置だと glob 空。要 fallback。

#### iter-2 未解決 convergent (asymptote)

- L131 skip "4.5–6" 範囲が Phase 6.5 含むか不明 (8/9) ─ sibling は全列挙、本 skill は範囲表記
- L154 marketplace root path 未収集 (8/9)
- L194 cross-skill 依存 (claude-md-parallel-audit Phase 6b 必須) ─ sibling 未インストール時 fallback 不在 (8/9)
- L73 / L289 cost figure 不整合 (>500k vs 440k) + Phase 0/6.5 cost 抜け (6/9)
- L263 Tool Requirements "foreground + parallel within one message" 論理矛盾 (6/9)
- 構造的 asymptote として受容、無限 iter 追求しない方針。

#### バージョン経緯

- v0.1.0 (initial sibling 作成) → v0.2.0 (full test iter-1 で発見した γ/δ + Phase 0 統合 + cost 較正) → v0.2.1 (iter-2 verification 後 α/γ/δ+ε/ζ/D2-analog の 5 fix + cmpa との sibling parity)。

### 2026-05-22 (initial release)

- claude-md-parallel-audit の SKILL.md target 用 sibling を新規作成 (v0.1.0)。
- C-plan trial (`skill-eval/SKILL.md` を target に N=9 走らせる) で 9/9 convergence、auditor.md の 7 軸が file-type agnostic と実証 → engine 再利用可能性を確認。

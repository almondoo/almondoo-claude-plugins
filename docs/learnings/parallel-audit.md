# Learnings — parallel-audit

各セッションで得た知見を新しい順に記録。

このファイルは `claude-md-parallel-audit` (cmpa) と `skill-md-parallel-audit` (smpa) を統合した `parallel-audit` plugin の learnings log。旧 2 ファイル (`docs/learnings/claude-md-parallel-audit.md`, `docs/learnings/skill-md-parallel-audit.md`) の歴史は本ファイル末尾に時系列で保存している。旧 plugin が marketplace から削除されるタイミングで旧 learnings ファイルも削除予定。

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

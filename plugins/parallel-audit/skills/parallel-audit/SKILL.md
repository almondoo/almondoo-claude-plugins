---
name: parallel-audit
description: Multi-agent parallel audit of CLAUDE.md, CLAUDE.local.md, AGENTS.md, GEMINI.md, or SKILL.md files for cross-section contradictions, missing qualifiers, terminology drift, and unstated premises. Use this skill whenever the user asks to audit, review, verify, quality-check, or convergence-check one of these files — even without the word "audit" — or mentions a recent refactor, a rule being ignored, observed behavior drift, a pre-shipping check before publishing a plugin, or accumulated session learnings. Dispatches N independent subagents (default 3), keeps only findings flagged by ≥threshold (default 2), classifies redundancy, then proposes targeted fixes with per-fix user approval. Do NOT use for writing a new instruction file (use skill-creator), updating with session learnings (use revise-claude-md), or auditing source code or non-markdown configs.
---

# parallel-audit

## Purpose

Long agent-instruction markdown files (CLAUDE.md, CLAUDE.local.md, AGENTS.md, GEMINI.md, SKILL.md) accumulate subtle defects over time: missing qualifiers, terminology drift between sections, implicit premises, ad-hoc enumerations, cross-section logical contradictions. A single audit pass — even a careful one — misses some defects and over-flags others.

The fix is to dispatch **multiple independent audits in parallel** and treat findings that **multiple independent auditors flag** as the high-confidence signal. Findings flagged by only one auditor are likely noise; findings flagged by ≥ threshold (default 2 of 3) are likely real.

This skill implements that workflow end-to-end: symptom triage → scope narrowing → parallel dispatch → reproducibility aggregation → false-positive filtering → redundancy classification → fix drafting → safety check → per-fix user approval → apply → post-fix verification → convergence check.

## Positioning: event-driven diagnostic, not routine maintenance

**This skill is designed for specific symptoms, not for daily / weekly / scheduled use.** The 7-axis taxonomy is generic enough that auditors will always find *something* in any prose, and the residual findings reach an asymptote that no number of iterations clears. Routine use therefore wastes tokens on noise the user already saw last time.

Intended trigger events:

- **Right after a large refactor** (added or restructured multiple rules) — new wording often contains undetected cross-section contradictions
- **A specific rule appears to be ignored / misapplied** — focused audit on that section + neighbors can surface conflicting rules or unstated premises
- **Observed agent behavior drift** — diagnostic to isolate whether the instruction file is the cause vs. model / hooks / prompt
- **After a Claude model upgrade** — wording the previous model accepted may parse differently now
- **`N` session learnings have accumulated** (e.g., via revise-claude-md) — incremental additions are a known source of cross-section contradictions

Anti-pattern: "let me run this weekly to keep my CLAUDE.md clean." The skill explicitly warns on routine selection in Phase 1 and asks the user to confirm before proceeding.

Defaults reflect the diagnostic positioning: `N=3` (not 9), `threshold=2` (not 4), `max_iterations=3` (not 5). Users can opt into the deeper `N=9` configuration in Phase 2 when the case justifies the cost.

## When to use

Trigger this skill when the user:

- Asks to **audit / review / verify / quality-check** an instruction file (CLAUDE.md, CLAUDE.local.md, AGENTS.md, GEMINI.md, SKILL.md)
- Wants to find **omissions / inconsistencies / contradictions / coherence issues** in such a file
- Mentions **multi-agent audit**, **parallel review**, **convergence audit**, **independent verification**, **audit my SKILL.md**, **review my CLAUDE.md after refactor**
- Reports a **specific symptom** (rule being ignored, behavior drift, post-refactor verification)
- Wants high-confidence reproducibility on long instruction file defects

Do NOT use this skill for:

- Writing a new CLAUDE.md from scratch (use `init` or `claude-md-improver`)
- Updating CLAUDE.md with session learnings (use `revise-claude-md`)
- Template-based gap analysis (use `claude-md-improver`)
- Authoring a brand new SKILL.md or running with-skill vs without-skill A/B benchmarks (use `skill-creator`)
- Auditing non-instruction files (source code, regular docs, READMEs)

## Target types

The skill detects `target_type` from the target file path (case-sensitive — the Claude Code spec requires uppercase `SKILL.md` / `CLAUDE.md`) and loads the corresponding specifics document:

| Target type | Detection | Specifics document |
|---|---|---|
| `claude-md` | Path ends in `CLAUDE.md`, `CLAUDE.local.md`, `AGENTS.md`, `GEMINI.md` | `references/claude-md-specifics.md` |
| `skill-md` | Path ends in `SKILL.md` | `references/skill-md-specifics.md` |

The specifics documents own: target-type-specific exclusion defaults, target-type-specific common false-positive patterns, target-type-specific Phase 11 behavior (e.g., CLAUDE.md inside `~/.claude/` triggers the auto-mode classifier; SKILL.md inside `plugins/<name>/skills/<name>/` does not), and any target-type-specific Phase 11.5(c) integration (currently SKILL.md only, via `skill-eval` static check).

Read the relevant specifics document **once** at Phase 2 after `target_type` is determined. Pass its content as additional context to Phase 4 auditors via the exclusion list, to Phase 7 redundancy-checker as the upstream-reference set, and to Phase 11 as the apply playbook.

## Configuration parameters

Defaults shown. Phase 2 asks the user to confirm or override.

| Parameter | Default | Description |
|---|---|---|
| `target_file` | (from initial message, or asked) | Absolute path of the file to audit |
| `target_type` | (auto-detected) | `claude-md` or `skill-md` (from file path) |
| `N` | 3 | Number of parallel auditor subagents per iteration. Opt-in to 5 or 9 for deeper convergence |
| `threshold` | 2 | Minimum instances that must flag an issue for it to be considered reproducible (≥2/3 ≈ 67%) |
| `max_iterations` | 3 | Hard upper bound on audit→fix→verify cycles. Reflects the empirically observed asymptote |
| `exclusions` | (asked, with target-type defaults pre-loaded) | Items the user does NOT want re-flagged. See `references/<target>-specifics.md` for pre-loaded defaults |
| `section_purposes` | (built at Phase 3) | Map from each section heading to its 1-line purpose; established once per audit and reused across iterations |
| `ab_testing_enabled` | `false` | Whether Phase 11.5(b) runs a `skill-eval` A/B benchmark after fixes. Opt-in only; requires `skill-eval` to be installed separately (it is not bundled in this marketplace). See `references/ab-testing.md` |
| `model_string` | `"sonnet"` | The string passed as the Agent tool's `model` parameter for Phase 4 parallel auditors. Default `"sonnet"` resolves to the current Sonnet generation at dispatch time. The user may override at Phase 2 by specifying a full model ID (e.g., `"claude-sonnet-4-6"`) for version-pinned reproducibility across an audit |

### Default calibration

Why these defaults?

- **`threshold = 2` (≥2/3 ≈ 67%)** — chosen over majority (50%) and supermajority (75%). At 67% (≥2/3), one missed-by-one-auditor real defect is still recovered by the other two. Moving to 75% (e.g., `N=4 / threshold=3`) requires three auditors to independently converge on the same true positive — too restrictive for genuine HIGH-severity prose defects given inter-instance variance. Moving down to 50% (e.g., `N=4 / threshold=2`) re-admits single-pair false positives that the multi-agent design was built to filter. Note: the 67% framing anchors on default `N=3`. At opt-in `N=5 / threshold=3` the bar is 60%, and at `N=9 / threshold=4` it is 44% — deeper tiers buy redundancy (more independent corroborators in absolute count), not stricter percentage agreement.
- **`N = 3`** — minimum N for ≥2 to be meaningful (2/2 is unanimous; 2/3 is convergence). Higher N (5, 9) buys statistical power but multiplies cost and rarely changes the convergent-issue set for files under ~500 lines.
- **`max_iterations = 3`** — empirically observed asymptote (see Positioning section). Iterations 4+ tend to produce diminishing real defects and increasing noise from previously-discussed exclusions.
- **`model_string = "sonnet"`** — Phase 4 is the only place this skill overrides parent-model inheritance. The ≥threshold aggregation absorbs per-instance noise, so Sonnet's HIGH-severity prose detection quality suffices at much lower per-token rates than Opus. Phases 6.5/7/9 still inherit the parent model since each is a single-agent evaluation with no aggregation buffer.

## Workflow

The skill runs in phases grouped as **Pre-check → Setup → Detect → Triage → Fix → Apply → Verify**. Each phase has a clear precondition and output. Do not skip phases unless explicitly noted.

---

### Pre-check

#### Phase 1: Symptom interview (always)

Read `references/symptom-interview-protocol.md` and follow its protocol to structure the user's reason for invoking the skill. Use **AskUserQuestion** to present the symptom options. Possible answers shape the rest of the workflow:

- **Post-refactor verification** → keep full-file scope in Phase 1.5; standard exclusions
- **Specific rule ignored / misapplied** → Phase 1.5 narrows to that rule + neighbors
- **Behavior drift** → full-file scope; consider `ab_testing_enabled: true` in Phase 2
- **Pre-shipping check** (SKILL.md before publishing a plugin) → full-file scope; ensure Phase 2.5 static check runs
- **Post-model-upgrade isolation** → full-file scope; standard exclusions
- **Routine maintenance** → emit warning per `references/symptom-interview-protocol.md` and require explicit confirmation to proceed

The symptom answer is stored as `symptom` and passed to Phase 1.5 to determine scope, and to Phase 11.5(b) decision.

#### Phase 1.5: Scope narrowing (always)

Based on the Phase 1 `symptom`, choose audit scope:

- **Full file** (default for most symptoms): auditors read the entire `target_file`
- **Section scope** (when symptom names a specific section): auditors read only the named section ± 30 lines of surrounding context
- **Rule-and-neighbors scope** (when symptom names a specific rule being ignored): auditors read the rule ± 20 lines AND grep the rest of the file for terms appearing in the rule, reading any other section that references those terms

For non-full scopes, the prompt placeholder `scope_directive` (substituted in Phase 4) tells auditors which lines to read instead of the whole file. This typically cuts per-instance token usage to 1/3–1/5 of full-file audit.

Confirm the chosen scope with **AskUserQuestion** before proceeding (one option per scope type plus "let me specify lines").

---

### Setup

#### Phase 2: Inputs + exclusions (always)

Use **AskUserQuestion** to collect:

1. **Target file path** (absolute path) — if not already provided in the user's initial message
2. **Confirm `target_type`** — show the auto-detected value, let the user override
3. **Confirm `N` / `threshold` / `max_iterations`** — defaults `3 / 2 / 3`. Offer an "opt into deep audit (N=5 or N=9)" option for cases where the user wants stronger convergence; show the per-iteration cost estimate for each tier
4. **Exclusions** — pre-load defaults from `references/<target_type>-specifics.md`. Present as multi-select for deselection, accept free-text additions for skill-specific intentional design
5. **A/B testing** — `ab_testing_enabled`? Default `false`. Show `references/ab-testing.md` cost estimate (typically doubles iteration cost) so the user can decide

The exclusion list is critical — without it, subagents will repeatedly flag intentional design as "issues" and convergence will never be reached.

#### Phase 2.5: Static pre-check (SKILL.md target only, when `skill-eval` is available)

Per `references/skill-md-specifics.md`, if `target_type == "skill-md"` AND the `skill-eval` skill is installed AS AN EXTERNAL DEPENDENCY, run its `static_check.py` and capture the result. This (a) hard-fails the audit if the SKILL.md is structurally broken, (b) gives Phase 4 auditors a baseline of structural axes already covered so they don't re-flag them, and (c) calibrates Phase 2 defaults for short / long SKILL.md bodies.

**Important**: `skill-eval` is NOT bundled in this marketplace (`almondoo-claude-plugins`). The integration is preserved as an optional capability: if the user has installed `skill-eval` from a different source (or has its source available on disk), the orchestrator can invoke it. If not installed, Phase 2.5 is **skipped without error** (log a one-line warning "Phase 2.5 skipped — `skill-eval` not available; structural axes will not be pre-cleared from the prose audit"). Resolution strategy for the skill-eval path is documented in `references/skill-md-specifics.md`.

When Phase 2.5 successfully produces a `static.json`, append the conditional 5th exclusion item (see `references/skill-md-specifics.md` exclusion #5) to the Phase 2 exclusion list **before Phase 4 dispatches**, so auditors receive the skill-eval delegation context and do not re-flag axes already covered.

If `target_type == "claude-md"`, skip Phase 2.5 entirely (the structural-axis delegation is SKILL.md-specific).

#### Phase 3: Section purposes baseline (always)

Phase 9 (`fix-safety-checker`) needs an explicit baseline of what each section is intended to do. Without this baseline, "intent preservation" gets judged by re-reading the same section the fix is editing — circular reasoning that can quietly accept fixes that distort intent.

Process:

1. Read `target_file` with Read (full file regardless of audit scope — the baseline must cover the whole file).
2. For each top-level heading (`## H2`) and meaningful sub-section (`### H3`), draft a 1-line purpose summary based on what the section's rules collectively do.
3. Present all section purposes as a **batch** via AskUserQuestion. Show the full list in the question description (one section per line: `## section-name → 1-line purpose`), then offer "All purposes look right" / "Some need correction — let me revise".
4. Store the confirmed purposes as `section_purposes`. Pass to Phase 7 (`redundancy-checker`) and Phase 9 (`fix-safety-checker`).

This phase runs once per audit, not per iteration.

---

### Detect

#### Phase 4: Parallel audit dispatch (always)

Read `agents/auditor.md` and use its full content as the prompt for each subagent. Substitute the placeholders (`target_file_path`, `related_files_paths`, `exclusion_list`, `scope_directive` from Phase 1.5) with the values collected so far. The prompt must be **byte-identical** across all N instances — same placeholder substitution, no per-instance variation.

Dispatch all `N` subagents in **one tool-call message** with `run_in_background: true`, `subagent_type: general-purpose`, and `model: "sonnet"`.

Pass `model_string` (default `"sonnet"`) to the `model` parameter — always pass it explicitly, even when the parent is already Sonnet, so the dispatch shape stays uniform. The user may override at Phase 2 with a full model ID (e.g., `"claude-sonnet-4-6"`) for version-pinned reproducibility; the same value is reused across iterations. Phase 4 is the **only** place this skill overrides parent-model inheritance — at Opus-level parent rates, N × iter cost would explode, and the ≥threshold aggregation absorbs per-instance noise so Sonnet's HIGH-severity detection quality suffices. Phases 6.5 / 7 / 9 must still inherit the parent model: each is a single-agent evaluation with no aggregation buffer, so their judgments need parent-level quality.

Critical requirements:

- All N subagents launched in the **same tool-call message** with `run_in_background: true`
- The prompt is `agents/auditor.md` content with placeholders substituted — byte-identical across instances
- Do NOT append "be honest" / "no sycophancy" / "be thorough" — the user's CLAUDE.md Forthright Assessment rules already cover this; extra instructions bias the audit
- Do NOT modify the 7 axes, output format, or "what not to flag" section in `agents/auditor.md` per-iteration. Touch only the placeholders.

**Failure handling for partial returns**: subagents can time out, return malformed (non-table) output, or never complete. Track the number of instances that returned parseable HIGH-issue output (`N_received`) versus dispatched (`N_dispatched`). If `N_received < N_dispatched`:

- Adjust the working threshold for this iteration to `max(2, ceil(N_received × threshold / N_dispatched))` so the convergence math is not broken by silent drop-outs. Never go below 2 — a single auditor's report is not "convergence". Trade-off: this keeps the *percentage* convergence threshold roughly stable but lowers the *absolute count* of corroborators. If your bar is the absolute count (e.g., "I require at least 4 independent flags before I act"), the alternative policy is to abort the iteration entirely on any drop-out and re-dispatch with a fresh N. The proportional formula is the default to keep audits from stalling on transient failures; switch to the abort-and-redispatch policy when count-based convergence is non-negotiable.
- If `N_received < 2`, abort the iteration and report the degradation to the user before re-dispatching or stopping. Single-instance results are noise, not signal.
- Surface degradation explicitly in Table A by adding a row `N_dispatched=X, N_received=Y, working_threshold=Z` so the user sees that Phase 5 aggregation used a different threshold than the configured `threshold`. Pass the `working_threshold` (not the configured `threshold`) into the Phase 12 Run parameters report so the trajectory is reproducible.

#### Phase 5: Aggregate (always)

When all N subagents complete, capture HIGH issues and build two tables:

**Table A: Per-instance HIGH count**

| Instance | HIGH count | Main flag content (short) |
|---|---|---|
| #1 | … | … |
| #2 | … | … |
| … | … | … |
| **avg** | **X.X** | |

**Table B: Convergent issues (≥ threshold)**

For each distinct issue mentioned across instances, count how many instances flagged it. Cluster similar findings (same Line + same root cause, even if phrasing differs). Report all issues with count ≥ threshold.

| # | Issue summary | Instances flagged | Count | Known tension? |
|---|---|---|---|---|
| A | … | #1, #3 | 2/3 | ❌ fix candidate |
| B | … | #2 | 1/3 | — (below threshold) |

**Aggregation drift hedge**: Do not unilaterally downgrade subagent verdicts. If you (the main thread) believe an issue at-or-above threshold is actually acceptable, do **not** quietly drop it — surface the disagreement to the user in Phase 6 triage. Main-thread session context biases toward agreement with the user (sycophancy gradient); subagents read in fresh contexts and their independent judgment is the trust anchor of this skill. If you find yourself softening a finding because "it doesn't feel like a defect", that's exactly the drift this hedge prevents — leave the call to the user.

---

### Triage

#### Phase 6: Triage + false-positive filter (when convergent issues exist)

For each convergent issue (count ≥ threshold), categorize:

- **Fix candidate**: New reproducible issue not in the exclusion list → forward to Phase 6.5
- **Acceptable**: Matches an exclusion the user provided → note and skip
- **Below threshold**: count < threshold → note in the table but do not propose a fix

If 0 fix candidates remain after this categorization, skip Phases 6.5, 7, 8, 9, 10, 11, 11.5(a), 11.5(b), and 11.5(c) entirely — no fix drafting, no application, no re-dispatch — and go directly to Phase 12 (stop check). No fixes were applied this iteration, so Phase 11.5(a)'s "fixes applied" precondition is not met and the re-dispatch has nothing to verify. Phase 12 evaluates whether to stop (`0 fix candidates from Phase 6` is a documented stop condition) or to continue with the next iteration if `max_iterations` is not yet reached.

#### Phase 6.5: False-positive detection (when fix candidates exist)

Read `agents/false-positive-detector.md` and dispatch one subagent (foreground, parent model inherited) with:

- `target_file`: the audit target path
- `related_files`: any project-level CLAUDE.md, CLAUDE.local.md, settings.json, etc.
- `convergent_issues`: the fix candidates from Phase 6
- `exclusion_list`: the current exclusion list (including any items added during this iteration)

Filter out FALSE issues — they do not become fix proposals. For NEEDS_HUMAN issues, surface them to the user in Phase 10 with the agent's reasoning so the user can decide.

#### Phase 7: Redundancy classification (when REAL fix candidates remain)

Read `agents/redundancy-checker.md` and dispatch one subagent (foreground, parent model inherited) with:

- `target_file`: the audit target path
- `target_type`: from Phase 2 — determines whether the checker compares against Claude Code defaults (`claude-md`) or sibling skills (`skill-md`)
- `convergent_issues`: REAL fix candidates from Phase 6.5, with cited section text (line ± 10 lines)
- `section_purposes`: from Phase 3
- `sibling_skills`: only for `target_type == "skill-md"` — list of installed sibling skill names + descriptions. The orchestrator resolves these via the strategy in `references/skill-md-specifics.md` "Marketplace root detection"; if no marketplace layout is found, pass an empty list

The subagent returns KEEP / SIMPLIFY / REMOVE per issue. Trust the classification, but if it returns REMOVE for a rule you (the main thread) believe has unique value, surface the disagreement to the user — same drift-hedge logic as Phase 5.

---

### Fix

#### Phase 8: Fix drafting (when REAL fix candidates remain)

For each REAL fix candidate, draft a fix matching its Phase 7 classification:

- **KEEP** → refine the wording to address the convergent issue
- **SIMPLIFY** → compress the rule to only its unique-value portion (use Phase 7's `suggested_action` as a hint)
- **REMOVE** → delete the rule entirely (optionally with a 1-line pointer to the canonical source)

Read the target file with Read to verify current line numbers and content before drafting.

**Draft mode**

- **Multi-option mode** (2–3 alternatives, each labeled with its trade-off) when the fix is *substantive*: it restructures a rule (move / split / merge), offers a meaningful KEEP vs SIMPLIFY vs REMOVE choice, or changes more than ~3 lines on either side of the diff.
- **Single-proposal mode** (one before/after diff) for ≤ 3-line wording tweaks with no structural change and no meaningful alternative.

When in doubt, use multi-option mode. It shifts the decision from "do you agree with my fix?" to "which alternative fits your intent?" — giving the user more agency on substantive changes, at the cost of one extra option to read.

#### Phase 9: Fix safety check (before showing each fix to user)

Read `agents/fix-safety-checker.md` and dispatch one safety-checker subagent **per fix** (or per option in multi-option mode) — spawn all such checkers in parallel within **one tool-call message** with `run_in_background: true`, parent model inherited. The orchestrator awaits all completions before proceeding to Phase 10 (each safety-check gates that fix's user approval question). Pass:

- `target_file`: the audit target path
- `issue_summary`: 1-2 lines describing the convergent issue this fix addresses
- `proposed_fix`: before/after diff, rationale, Phase 7 classification
- `section_purposes`: from Phase 3 (authoritative intent baseline; do not re-derive from file content)

Verdict handling:

- **SAFE** → present to user in Phase 10
- **UNSAFE** → do NOT present this fix as-is. Re-draft addressing the concerns, or escalate with explicit warnings
- **NEEDS_REVIEW** → present with trade-offs clearly stated in the AskUserQuestion description
- **`rule_burden_impact: INCREASES_MAJOR`** → regardless of verdict, surface prominently. Adding rules has real cost

#### Phase 10: User approval per fix

For each fix candidate, present via **AskUserQuestion**. One question per fix candidate — do not batch.

**Single-proposal mode options:**

- Apply this fix
- Skip (add to exclusion list as architectural tension)
- Modify (user provides alternative wording)

**Multi-option mode options:**

- Option A: [strongest compression — typically REMOVE — with 1-line trade-off label]
- Option B: [middle ground — typically SIMPLIFY]
- Option C: [conservative — typically KEEP with refinement]
- Skip (add to exclusion list)
- Modify (user provides different wording)

Include trade-off labels in option descriptions so the user sees why each option exists.

---

### Apply

#### Phase 11: Apply via Edit (when fixes approved)

**Pre-authorize when target is on the classifier trigger list.** For any `claude-md` target or installed `skill-md` target (see trigger-location tables in `references/claude-md-specifics.md` and `references/skill-md-specifics.md`), the classifier trigger is deterministic — issuing Edit first WILL block. **Do not issue Edit first.** Use **AskUserQuestion** immediately with the "Yes, update my `<file>`" template from the playbook, then issue Edit after the explicit authorization. If pre-authorization happens to not release the classifier on the first Edit attempt (the playbook documents release on retry after authorization), use the same authorization to retry. Either way, the user has already authorized — you have eliminated the "block → think → look up playbook → ask → answer" thinking round-trip that the reactive path costs.

For targets NOT on the trigger list, just use **Edit** directly. If the classifier still blocks (rare), fall back to the playbook in `references/claude-md-specifics.md` reactively — it owns the canonical trigger-location table and the "Yes, update my `<file>`" authorization template. For SKILL.md location nuances (marketplace source vs installed), see `references/skill-md-specifics.md` "Phase 11 location-aware classifier behavior".

After all Edit calls, briefly confirm what was applied (file list + 1-line description per fix).

#### Phase 11.5: Post-fix verify

Run the applicable verification layers:

- **11.5(a) Audit re-dispatch (always when fixes applied and iteration < max_iterations)** → re-dispatch N subagents (same prompt, with updated exclusion list if any added in Phase 10) and repeat Phases 4–6. If new fix candidates appear, run the full Phase 6.5–11 cycle. Phase 3 `section_purposes` are stable across iterations and re-passed unchanged unless the user explicitly says the section structure changed
- **11.5(b) A/B benchmark (only when `ab_testing_enabled: true` AND `skill-eval` is installed externally)** → see `references/ab-testing.md`. Runs `skill-eval`'s with/without comparison on a user-supplied benchmark task set, before vs after the iteration's fixes. The skill does NOT automatically curate the task set — the user must provide it. If `skill-eval` is not available, Phase 11.5(b) is skipped with a warning even when `ab_testing_enabled: true` (the user opted in but the dependency is missing; surface this prominently so the user can install skill-eval and re-run, or accept the audit without A/B verification)
- **11.5(c) Static re-check (only when `target_type == "skill-md"` and Phase 2.5 ran)** → re-execute `skill-eval`'s `static_check.py` on the target. Result feeds the Phase 12 ship-ready stop criterion. If Phase 2.5 was skipped (skill-eval unavailable), Phase 11.5(c) is automatically skipped too

---

### Verify

#### Phase 12: Stop condition check (always after each iteration)

Stop and report final state when **any primary** stop condition holds. The ship-ready row at the bottom is **additive** — it never stops the workflow on its own, it only enriches a primary stop's final report when also satisfied.

| Condition | Type | Interpretation |
|---|---|---|
| All N instances report "NO HIGH ISSUES" | primary | Full convergence — file is clean |
| At least `(N − threshold + 1)` instances report "NO HIGH ISSUES" (default: ≥2 of 3 when N=3 / threshold=2) | primary | Practical convergence — even if every remaining instance flagged the same issue, it could not reach `threshold`, so no reproducible defect can remain |
| HIGH avg plateau for 2 consecutive iterations (avg change < 1) | primary | Structural limit reached — remaining issues are likely deliberate design / architectural tensions |
| iteration ≥ `max_iterations` | primary | Hard limit — report current state, flag the asymptote explicitly |
| 0 fix candidates from Phase 6 | primary | Nothing actionable left |
| Phase 11.5(c) static.json reports `score == 1.0 AND warnings == 0` (SKILL.md target only, when Phase 2.5 ran) | additive | Structurally ship-ready on the static layer. When ALSO combined with full convergence or practical convergence above, report "both layers clean". Never a standalone stop: if no primary row holds, do not stop on this row alone, and conversely `warnings > 0` alone is not a stop reason either — only the absence of primary stop conditions is. |

**Derivation of `(N − threshold + 1)` (practical-convergence row).** If `(N − threshold + 1)` instances independently report "NO HIGH ISSUES", then at most `threshold − 1` instances could still flag any given issue. Since the convergence rule requires `≥ threshold` instances to flag the same issue before it counts as a real defect, no reproducible defect can possibly remain — even in the worst case where every remaining instance flagged the same thing. For defaults `N=3 / threshold=2`, this is `≥ 2 of 3` reporting clean. This stop condition is target-type agnostic (applies to both `claude-md` and `skill-md` targets) — keep the derivation here rather than in target-specifics docs.

Report the iteration history (Phase 5 tables across all iterations) so the user can see the trajectory.

## Audit prompt

The audit prompt lives in `agents/auditor.md`. Phase 4 reads that file and uses its full content as the subagent prompt (with placeholders substituted). The 7 axes, the "no collusion" framing, the strict HIGH-only filter, and the exclusion handling are file-type agnostic and have been validated on both CLAUDE.md and SKILL.md targets.

Do not duplicate the prompt here. The single source of truth is `agents/auditor.md`. Editing the prompt means editing that file.

## Output format

After all iterations complete, present a final report. The **Run parameters** block is required — it lets the user verify which configuration produced the trajectory below, especially when defaults were overridden at Phase 2.

```
## Audit complete — final report

### Run parameters

| Parameter | Value |
|---|---|
| Target | `<target_file>` (type: `<target_type>`) |
| Symptom | `<symptom>` (routine_override: `<true|false>`) |
| N / threshold / max_iterations | `<N> / <threshold> / <max_iterations>` |
| Phase 4 working threshold | `<working_threshold>` (`= threshold` unless C1 degradation fired on some iteration) |
| Exclusions | `<count>` items applied (`<default_count>` from `references/<target_type>-specifics.md` + `<user_added_count>` user-added; full list in Phase 2 log) |
| Phase 4 model | `<model_string>` |
| ab_testing_enabled | `<true|false>` |
| Iterations actually run | `<count>` of `<max_iterations>` max |

### Iteration trajectory

| Iteration | HIGH avg | Convergent issues | Fixes applied | Status |
|---|---|---|---|---|
| 1 | 3.3 | 2 | 2 | continued |
| 2 | 0.7 | 0 | 0 | converged (≥2/3 said clean — practical convergence at N=3/threshold=2) |

### Fixes applied
- (line range) before → after — 1-sentence rationale
- ...

### Remaining accepted exclusions (carried over)
- ...

### Recommendation
[Specific recommendation based on convergence pattern — e.g., "file is now in good shape", or "consider re-running with relaxed exclusions if you want to re-examine known tensions", or "asymptote reached at N=3; for stronger signal re-run with N=9 deep audit"]
```

## Tool requirements

| Tool | Use |
|---|---|
| `Agent` | Parallel subagent dispatch (Phase 4 audit, Phase 6.5 false-positive, Phase 7 redundancy, Phase 9 safety). `run_in_background: true` for Phase 4 (N parallel auditors); Phase 6.5 / 7 each run a single subagent (`run_in_background: false` is fine since there is nothing to parallelize with); Phase 9 dispatches 1 per fix candidate (or 1 per option) in parallel within a **single tool-call message** with `run_in_background: true` and awaits all completions before Phase 10 (the orchestrator gates each Phase 10 approval question on its safety-checker result) |
| `Read` | Phase 1 (read `references/symptom-interview-protocol.md`); Phase 3 (section purposes); verify line numbers before Phase 8 drafting; read `agents/*.md` when dispatching specialized subagents; read `references/<target_type>-specifics.md` at Phase 2; read `references/ab-testing.md` at Phase 2 when `ab_testing_enabled` is being decided |
| `AskUserQuestion` | Phase 1 symptom interview, Phase 1.5 scope confirmation, Phase 2 setup, Phase 3 section purposes confirmation, Phase 10 fix approval, Phase 11 auto-mode classifier authorization (per `references/claude-md-specifics.md`) — never use plain-text questions per CLAUDE.md communication rule |
| `Edit` | Apply approved fixes; follow `references/claude-md-specifics.md` playbook when blocked |
| `Glob` | Phase 7 sibling-skill discovery (`target_type == "skill-md"` only); Phase 2 SKILL.md candidate discovery when user passes a plugin root instead of a SKILL.md path |
| `Bash` | Phase 2.5 / 11.5(c) `skill-eval static_check.py` execution; Phase 11.5(b) optional `skill-eval` benchmark execution |

## Common pitfalls

See `references/pitfalls.md` for the grouped list (workflow / aggregation / fix-proposal / target-specific). Consult it when a phase isn't behaving as expected or when onboarding.

## Cost notes

Cost scales with `N`, `max_iterations`, and the number of REAL fix candidates that survive Phase 6.5/7.

| Tier | N / threshold | Phase 4 audit dispatch (approx, Sonnet-pinned) | Verification overhead per iteration (Phase 6.5/7/9, parent model) | When to use |
|---|---|---|---|---|
| Quick (default) | 3 / 2 | ~150k tokens | +20–80k tokens (scales with fix candidate count) | Symptom-driven diagnostic; standard event-driven use |
| Standard | 5 / 3 | ~280k tokens | +20–80k tokens | When N=3 convergence feels weak |
| Deep (opt-in) | 9 / 4 | ~440k tokens | +20–80k tokens | Pre-shipping check on a high-leverage instruction file, or when N=3 / 5 didn't converge |

**Parent-model multiplier.** Phase 4 is Sonnet-pinned but Phases 6.5/7/9 inherit the parent model. At an Opus parent session, verification overhead is priced at Opus rates, so a Quick-tier iteration with 3 fix candidates totals roughly 250–300k tokens (150k audit + ~100–150k verification at Opus), not 150k. Multiply that by `max_iterations` (default 3) for the full audit budget. Phase 11.5(b) A/B benchmark roughly doubles the per-iteration cost when enabled (it runs skill-eval on the user-supplied task set before and after).

**Numbers are inferred, not measured.** The "+20–80k" verification range and the Opus 1.5–2× multiplier are derived from per-phase prompt size estimates, not from logged Phase 6.5/7/9 token counts in actual runs. Adjust based on observed token usage from your own audits — if you have data, update this table.

Surface the estimated total cost at Phase 2 so the user can downsize before dispatch. The cost is justified when the file is high-leverage (loaded into every Claude session) and an event-driven symptom triggered the audit. For routine maintenance, the cost is not justified — this skill is the wrong tool for that use case.

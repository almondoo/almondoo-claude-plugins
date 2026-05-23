---
name: parallel-audit
description: Event-driven multi-agent parallel audit of agent-instruction markdown files (CLAUDE.md / CLAUDE.local.md / AGENTS.md / GEMINI.md / SKILL.md) for HIGH-severity quality issues — missing qualifiers, grammar errors, terminology drift, cross-section logical contradictions, implicit premises, incomplete enumerations, and undefined terms. Dispatches N independent subagents (default N=3, opt-in N=9 for deep audit), aggregates findings by reproducibility threshold, filters shared blind spots, classifies redundancy against Claude Code defaults or sibling skills, and proposes targeted fixes via per-fix user approval. Use this skill when the user asks to audit / review / verify / quality-check an instruction file, mentions multi-agent audit / convergence audit / parallel review / instruction file consistency / audit my SKILL.md, has just refactored their CLAUDE.md and wants verification, notices a specific rule being ignored, observes agent behavior drift, or asks for high-confidence reproducibility on what is wrong with a long instruction file. Designed as event-driven diagnostic — Phase 1 warns on routine use. Distinct from template-comparison audits (e.g. claude-md-management:claude-md-improver) — this skill uses independent parallel audits + reproducibility threshold, not template matching. Successor to claude-md-parallel-audit + skill-md-parallel-audit, unified under a target_type parameter.
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

The skill detects `target_type` from the target file path and loads the corresponding specifics document:

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
| `target_file` | (asked) | Absolute path of the file to audit |
| `target_type` | (auto-detected) | `claude-md` or `skill-md` (from file path) |
| `N` | 3 | Number of parallel auditor subagents per iteration. Opt-in to 5 or 9 for deeper convergence |
| `threshold` | 2 | Minimum instances that must flag an issue for it to be considered reproducible (≥2/3 ≈ 67%) |
| `max_iterations` | 3 | Hard upper bound on audit→fix→verify cycles. Reflects the empirically observed asymptote |
| `exclusions` | (asked, with target-type defaults pre-loaded) | Items the user does NOT want re-flagged. See `references/<target>-specifics.md` for pre-loaded defaults |
| `section_purposes` | (drafted then asked in Phase 3) | Map from each section heading to its 1-line purpose; established once per audit and reused across iterations |
| `ab_testing_enabled` | `false` | Whether Phase 11.5(b) runs a `skill-eval` A/B benchmark after fixes. Opt-in only; see `references/ab-testing.md` |

## Workflow

The skill runs in phases grouped as **Pre-check → Setup → Detect → Triage → Fix → Apply → Verify**. Each phase has a clear precondition and output. Do not skip phases unless explicitly noted.

---

### Pre-check

#### Phase 1: Symptom interview (always)

Read `agents/symptom-interview.md` and follow its protocol to structure the user's reason for invoking the skill. Use **AskUserQuestion** to present the symptom options. Possible answers shape the rest of the workflow:

- **Post-refactor verification** → keep full-file scope in Phase 1.5; standard exclusions
- **Specific rule ignored / misapplied** → Phase 1.5 narrows to that rule + neighbors
- **Behavior drift** → full-file scope; consider `ab_testing_enabled: true` in Phase 2
- **Pre-shipping check** (SKILL.md before publishing a plugin) → full-file scope; ensure Phase 2.5 static check runs
- **Post-model-upgrade isolation** → full-file scope; standard exclusions
- **Routine maintenance** → emit warning per `agents/symptom-interview.md` and require explicit confirmation to proceed

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

Per `references/skill-md-specifics.md`, if `target_type == "skill-md"` and the `skill-eval` skill is installed, run its `static_check.py` and capture the result. This (a) hard-fails the audit if the SKILL.md is structurally broken, (b) gives Phase 4 auditors a baseline of structural axes already covered so they don't re-flag them, and (c) calibrates Phase 2 defaults for short / long SKILL.md bodies.

If `target_type == "claude-md"` or `skill-eval` is not available, skip Phase 2.5 entirely.

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

The `model: "sonnet"` value: pass the literal string `"sonnet"` — the Agent tool resolves this alias to the current Sonnet generation available in the harness. If the user wants version-pinned reproducibility across the audit, pass the full model ID instead (e.g., `claude-sonnet-4-6`). If the orchestrating parent model is already Sonnet, the override is effectively a no-op but the explicit `model` parameter is still required (do not omit it — the documented dispatch shape is uniform regardless of parent model).

Critical requirements:

- All N subagents launched in the **same tool-call message** (parallel dispatch)
- `run_in_background: true` so the harness notifies on completion
- **`model: "sonnet"` explicit override.** Phase 4 is the only place this skill overrides the parent-model-inheritance default. Rationale: when the parent model is more expensive than Sonnet (e.g., Opus), N×iter cost would explode at parent-model rates, and the ≥threshold aggregation absorbs per-instance noise so Sonnet's HIGH-severity detection quality suffices. When the parent IS Sonnet, the override is a no-op but stays explicit for consistency. Phases 6.5 / 7 / 9 (single-agent evaluation subagents — false-positive filtering, redundancy classification, fix safety verdict) must still inherit the parent's model: each runs once with no aggregation buffer, so their judgments need parent-level quality
- Do NOT add "be honest" / "no sycophancy" / "be thorough" instructions on top of `agents/auditor.md` — the user's CLAUDE.md Forthright Assessment rules already cover this and extra instructions bias the audit
- Do NOT modify the 7 axes, output format, or "what not to flag" section in `agents/auditor.md` per-iteration. Touch only the placeholders.

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
- `sibling_skills`: only for `target_type == "skill-md"` — list of installed sibling skill names + descriptions (the orchestrator collects via `Glob plugins/*/skills/*/SKILL.md` of the marketplace; if the target SKILL.md is not in a marketplace layout, pass an empty list)

The subagent returns KEEP / SIMPLIFY / REMOVE per issue. Trust the classification, but if it returns REMOVE for a rule you (the main thread) believe has unique value, surface the disagreement to the user — same drift-hedge logic as Phase 5.

---

### Fix

#### Phase 8: Fix drafting (when REAL fix candidates remain)

For each REAL fix candidate, draft a fix matching its Phase 7 classification:

- **KEEP** → refine the wording to address the convergent issue
- **SIMPLIFY** → compress the rule to only its unique-value portion (use Phase 7's `suggested_action` as a hint)
- **REMOVE** → delete the rule entirely (optionally with a 1-line pointer to the canonical source)

Read the target file with Read to verify current line numbers and content before drafting.

**Draft mode — single vs. multi-option**

For each fix, choose drafting mode by scope:

- **Single-proposal mode** (default): the fix is **trivial** — ≤3 lines changed, no structural change, no choice between substantially different approaches. Draft one before/after diff
- **Multi-option mode**: the fix is **substantive** — more than 3 lines changed, OR the fix restructures a rule, OR there's a meaningful choice between approaches (e.g., delete vs. compress vs. keep-with-refinement). Draft 2-3 alternative before/after options, each labeled with its trade-off

Multi-option mode shifts the decision from "do you agree with my fix?" to "which of these alternatives best fits your intent?" — giving the user more agency on substantive changes.

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

Use **Edit** to apply approved fixes. If the target is an agent-config file that trips the auto-mode classifier, follow the playbook in `references/claude-md-specifics.md` (the "Yes, update my `<file>`" authorization template, retry once). The classifier triggers depend on the target path:

- CLAUDE.md / CLAUDE.local.md at project root → triggers
- `~/.claude/CLAUDE.md`, `~/.claude/settings.json`, `~/.claude/settings.local.json` → trigger
- `.claude/skills/*`, `.claude/agents/*`, `.claude/hooks/*`, `.claude/commands/*`, `.mcp.json` → trigger
- SKILL.md inside `plugins/<name>/skills/<name>/` (marketplace source) → does NOT trigger (plugin artifact, not installed config)

After all Edit calls, briefly confirm what was applied (file list + 1-line description per fix).

#### Phase 11.5: Post-fix verify

Run the applicable verification layers:

- **11.5(a) Audit re-dispatch (always when fixes applied and iteration < max_iterations)** → re-dispatch N subagents (same prompt, with updated exclusion list if any added in Phase 10) and repeat Phases 4–6. If new fix candidates appear, run the full Phase 6.5–11 cycle. Phase 3 `section_purposes` are stable across iterations and re-passed unchanged unless the user explicitly says the section structure changed
- **11.5(b) A/B benchmark (only when `ab_testing_enabled: true`)** → see `references/ab-testing.md`. Runs `skill-eval`'s with/without comparison on a user-supplied benchmark task set, before vs after the iteration's fixes. The skill does NOT automatically curate the task set — the user must provide it
- **11.5(c) Static re-check (only when `target_type == "skill-md"` and Phase 2.5 ran)** → re-execute `skill-eval`'s `static_check.py` on the target. Result feeds the Phase 12 ship-ready stop criterion

---

### Verify

#### Phase 12: Stop condition check (always after each iteration)

Stop and report final state when **any** of these holds:

| Condition | Interpretation |
|---|---|
| All N instances report "NO HIGH ISSUES" | Full convergence — file is clean |
| At least `(N − threshold + 1)` instances report "NO HIGH ISSUES" (default: ≥2 of 3 when N=3 / threshold=2) | Practical convergence — even if every remaining instance flagged the same issue, it could not reach `threshold`, so no reproducible defect can remain |
| HIGH avg plateau for 2 consecutive iterations (avg change < 1) | Structural limit reached — remaining issues are likely deliberate design / architectural tensions |
| iteration ≥ `max_iterations` | Hard limit — report current state, flag the asymptote explicitly |
| 0 fix candidates from Phase 6 | Nothing actionable left |
| Phase 11.5(c) static.json reports `score == 1.0 AND warnings == 0` (SKILL.md target only, when Phase 2.5 ran) | Structurally ship-ready on the static layer; combine with practical convergence above for a "both layers clean" signal |

Report the iteration history (Phase 5 tables across all iterations) so the user can see the trajectory.

## Audit prompt

The audit prompt lives in `agents/auditor.md`. Phase 4 reads that file and uses its full content as the subagent prompt (with placeholders substituted). The 7 axes, the "no collusion" framing, the strict HIGH-only filter, and the exclusion handling are file-type agnostic and have been validated on both CLAUDE.md and SKILL.md targets.

Do not duplicate the prompt here. The single source of truth is `agents/auditor.md`. Editing the prompt means editing that file.

## Output format

After all iterations complete, present a final report:

```
## Audit complete — final report

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
| `Read` | Phase 3 (section purposes), verify line numbers before Phase 8 drafting, read `agents/*.md` files when dispatching specialized subagents, read `references/*-specifics.md` based on `target_type` |
| `AskUserQuestion` | Phase 1 symptom interview, Phase 1.5 scope confirmation, Phase 2 setup, Phase 3 section purposes confirmation, Phase 10 fix approval, Phase 11 auto-mode classifier authorization (per `references/claude-md-specifics.md`) — never use plain-text questions per CLAUDE.md communication rule |
| `Edit` | Apply approved fixes; follow `references/claude-md-specifics.md` playbook when blocked |
| `Glob` | Phase 7 sibling-skill discovery (`target_type == "skill-md"` only); Phase 2 SKILL.md candidate discovery when user passes a plugin root instead of a SKILL.md path |
| `Bash` | Phase 2.5 / 11.5(c) `skill-eval static_check.py` execution; Phase 11.5(b) optional `skill-eval` benchmark execution |

## Bundled agents

| Agent file | Used in | Dispatched | Purpose |
|---|---|---|---|
| `agents/auditor.md` | Phase 4 | N parallel (default 3), `run_in_background: true`, `model: "sonnet"` | Independent HIGH-severity audit along 7 axes; returns up to 10 findings as a markdown table. **File-type agnostic** — same axes apply to CLAUDE.md and SKILL.md targets |
| `agents/false-positive-detector.md` | Phase 6.5 | 1 foreground, parent model inherited | Independent re-read of each convergent issue to filter shared-blind-spot false positives |
| `agents/redundancy-checker.md` | Phase 7 | 1 foreground, parent model inherited | Classifies each REAL fix candidate as KEEP / SIMPLIFY / REMOVE. **Branches on `target_type`**: against Claude Code defaults for `claude-md`, against `skill-creator` / `skill-eval` / sibling skills for `skill-md` |
| `agents/fix-safety-checker.md` | Phase 9 | 1 per fix candidate (or 1 per option), dispatched in parallel within one tool-call message with `run_in_background: true`; orchestrator awaits all completions before Phase 10. Parent model inherited | Verifies fix does not break cross-section references, contradict other rules, distort intent; also reports `rule_burden_impact` (REDUCES / NEUTRAL / INCREASES_MINOR / INCREASES_MAJOR) |
| `agents/symptom-interview.md` | Phase 1 | (no subagent — read as protocol) | Structures the user's symptom answer into a scope hint for Phase 1.5 and a context hint for Phase 2 |

## Reference files

| Reference file | Loaded when | Owns |
|---|---|---|
| `references/claude-md-specifics.md` | `target_type == "claude-md"` | CLAUDE.md / CLAUDE.local.md / AGENTS.md / GEMINI.md exclusion defaults; auto-mode classifier playbook for Phase 11; common shared-blind-spot patterns for Phase 6.5 |
| `references/skill-md-specifics.md` | `target_type == "skill-md"` | SKILL.md exclusion defaults (subagent_type names, placeholder conventions, cross-skill informational pointers, frontmatter delegation to skill-eval); `skill-eval` integration for Phase 2.5 and Phase 11.5(c); common shared-blind-spot patterns specific to SKILL.md |
| `references/ab-testing.md` | `ab_testing_enabled: true` | Phase 11.5(b) integration with `skill-eval`'s with/without benchmark; user-supplied task set requirement; cost estimate; interpretation guidance for noisy small-effect-size differentials |

## Common pitfalls

- **Skipping Phase 1 symptom interview** → routine audits run by default. Always run Phase 1 even if the user "seems to know what they want"; the symptom shapes scope and A/B decision
- **Forgetting the exclusion list** → subagents re-flag intentional design every iteration; convergence never reaches. Always collect exclusions in Phase 2 with `references/<target>-specifics.md` pre-loaded defaults
- **Skipping Phase 3 section purposes** → `fix-safety-checker.intent_preserved` becomes circular (judged by re-reading the section being changed)
- **Batching all fix proposals into one question** → user rubber-stamps or rejects everything. One AskUserQuestion per fix
- **Skipping Phase 11.5(a) re-verify** → "I applied 2 fixes, done" is premature. Without re-verification, you don't know if fixes actually changed convergence behavior
- **Modifying the audit prompt to "improve" it** → breaks reproducibility. The 7 axes and exclusion section are load-bearing; touch only the placeholders
- **Dispatching subagents serially** → wastes time. Always dispatch all N in one message with `run_in_background: true`
- **Treating "below threshold" issues as fixable** → ≥ threshold is the bar. Below that, signal is too noisy to trust
- **Skipping Phase 6.5 / 7 / 9 verification subagents** → ≥threshold convergence does not guarantee correctness. The 3 phases catch shared-misreading false positives, redundant rules, and unsafe fixes
- **Letting Phase 9 verdict be overridden silently** → if `fix-safety-checker` returns UNSAFE, do not present that fix to the user unmodified
- **Main-thread aggregation drift** → quietly downgrading subagent findings during Phase 5 defeats the purpose of multi-agent audit. Subagents read in fresh contexts; you read with accumulated session bias
- **Refining a redundant rule instead of removing it** → honor Phase 7's REMOVE / SIMPLIFY classification
- **Using single-proposal mode for substantive fixes** → forcing the user into "Apply / Skip / Modify (free text)" wastes their time. Use multi-option mode when the fix is substantive
- **Retrying auto-mode-blocked Edits blindly** → without explicit AskUserQuestion authorization, the classifier blocks every retry. Follow the `references/claude-md-specifics.md` playbook
- **Ignoring `rule_burden_impact: INCREASES_MAJOR`** → adding rules has real cost. Surface major increases in the AskUserQuestion description, do not bury
- **Running routine without symptom** → Phase 1 emits a warning; honor it. Routine use of this skill is anti-pattern — the asymptote means the same findings recur and waste tokens
- **Treating cross-skill references as automatic defects (SKILL.md target)** → if the SKILL.md inlines the load-bearing content AND points to the canonical source as a courtesy, that is not a defect

## Cost notes

Cost scales with `N`, `max_iterations`, and the number of REAL fix candidates that survive Phase 6.5/7.

| Tier | N / threshold | Per-iteration cost (approx) | When to use |
|---|---|---|---|
| Quick (default) | 3 / 2 | ~150k tokens | Symptom-driven diagnostic; standard event-driven use |
| Standard | 5 / 3 | ~280k tokens | When N=3 convergence feels weak |
| Deep (opt-in) | 9 / 4 | ~440k tokens | Pre-shipping check on a high-leverage instruction file, or when N=3 / 5 didn't converge |

Multiply by `max_iterations` (default 3) for the full audit budget. Phase 11.5(b) A/B benchmark roughly doubles the per-iteration cost when enabled (since it runs skill-eval on the user-supplied task set before and after).

Surface the estimated total cost at Phase 2 so the user can downsize before dispatch. The cost is justified when the file is high-leverage (loaded into every Claude session) and an event-driven symptom triggered the audit. For routine maintenance, the cost is not justified — this skill is the wrong tool for that use case.

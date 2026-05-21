---
name: claude-md-parallel-audit
description: Multi-agent parallel audit of CLAUDE.md (or similar instruction files like CLAUDE.local.md, AGENTS.md, GEMINI.md) for HIGH-severity quality issues — missing qualifiers, grammar errors, terminology drift, cross-section logical contradictions, implicit premises, incomplete enumerations, and undefined terms. Dispatches N independent subagents to audit the same file, aggregates findings by reproducibility (≥4/9 default), distinguishes new fixable issues from known architectural tensions the user has accepted, and proposes targeted fixes via AskUserQuestion. Use this skill whenever the user asks to audit / review / verify / check the quality / consistency / integrity of a CLAUDE.md or similar agent instruction file, or mentions "multi-agent audit", "convergence audit", "parallel review", "instruction file consistency", finding inconsistencies / contradictions / omissions in instruction files, or wants high-confidence reproducibility on what's wrong with a long instruction file. Distinct from template-comparison audits (e.g. `claude-md-management:claude-md-improver`) — this skill specifically uses parallel independent audits + reproducibility threshold, not template matching.
---

# claude-md-parallel-audit

## Purpose

Long agent instruction files (CLAUDE.md, CLAUDE.local.md, AGENTS.md, GEMINI.md) accumulate subtle defects over time: missing qualifiers, terminology drift between sections, implicit premises, ad-hoc enumerations. A single audit pass — even a careful one — misses some defects and over-flags others (false positives that aren't really defects).

The fix is to dispatch **multiple independent audits in parallel** and treat findings that **multiple independent auditors flag** as the high-confidence signal. Findings flagged by only one auditor are likely noise. Findings flagged by ≥4 of 9 are likely real.

This skill implements that workflow end-to-end: setup → parallel dispatch → reproducibility aggregation → triage (new issues vs. known architectural tensions the user has already accepted) → fix proposal → user approval → apply → re-verify until convergence.

## When to use

Trigger this skill when the user:

- Asks to **audit / review / verify / check the quality** of a CLAUDE.md, CLAUDE.local.md, or similar instruction file
- Wants to find **omissions / inconsistencies / contradictions / coherence issues** in a long instruction file
- Mentions **multi-agent audit**, **parallel review**, **convergence audit**, **independent verification**
- Says the instruction file "feels inconsistent" or "I want a second opinion on this CLAUDE.md"
- Has already done a single-pass review and wants higher-confidence reproducibility data
- Wants to know which CLAUDE.md issues are **structural tensions** (acceptable) vs. **fixable defects** (worth editing)

Do NOT use this skill for:

- Writing a new CLAUDE.md from scratch (use `init` or `claude-md-improver` instead)
- Updating CLAUDE.md with session learnings (use `revise-claude-md` instead)
- Template-based gap analysis (use `claude-md-improver` instead)
- Auditing non-instruction files (source code, docs)

## Configuration parameters

Defaults shown. The skill should ask the user to confirm or override these at Phase 1.

| Parameter | Default | Description |
|---|---|---|
| `N` | 9 | Number of parallel subagents to dispatch per iteration |
| `threshold` | 4 | Minimum instances that must flag an issue for it to be considered reproducible (so ≥4/9 = ~44%) |
| `max_iterations` | 5 | Hard upper bound on audit→fix→verify cycles |
| `target_file` | (asked) | Absolute path of the file to audit (e.g. `~/.claude/CLAUDE.md`) |
| `exclusions` | (asked) | List of intentional design choices the user does NOT want flagged |
| `section_purposes` | (drafted then asked in Phase 1.5) | Map from each section heading to its 1-line purpose; established once per audit and reused across iterations |

## Workflow

The skill runs in phases grouped as **Setup → Detect → Triage → Fix → Apply → Verify**. Each phase has a clear precondition and output. Do not skip phases.

---

### Setup

#### Phase 1: Inputs (always)

Use **AskUserQuestion** to collect:

1. **Target file path** (absolute path)
2. **Confirm N / threshold / max_iterations** (default 9 / 4 / 5, override if user wants)
3. **Exclusions** — intentional design choices the user has already accepted and does NOT want re-flagged. Examples (collect from user, not from this list):
   - Specific sections that are intentionally absent
   - Architectural tensions known to be unresolvable
   - Style choices that look inconsistent but are intentional
   - Externally-defined concepts (e.g. Claude Code official terms) that don't need to be re-defined

The exclusion list is critical — without it, subagents will repeatedly flag intentional design as "issues" and convergence will never be reached.

#### Phase 1.5: Section intent baseline (always)

Phase 5.5 (`fix-safety-checker`) needs an explicit baseline of what each section is intended to do. Without this baseline, "intent preservation" gets judged by re-reading the same section the fix is editing — circular reasoning that can quietly accept fixes that distort intent. Establish the baseline here, once per audit.

Process:

1. Read the target file with Read.
2. For each top-level heading (`## H2`) and meaningful sub-section (`### H3`), draft a 1-line purpose summary based on what the section's rules collectively do.
3. Present all section purposes as a **batch** to the user via AskUserQuestion. Show the full list in the question description (one section per line: `## section-name → 1-line purpose`), then ask:
   - "All purposes look right" — proceed
   - "Some need correction — let me revise" — user provides corrections in free text, you re-confirm, then proceed
4. Store the confirmed purposes as `section_purposes` (a map from section heading → confirmed 1-line purpose). Pass this map to Phase 4.6 (`default-redundancy-checker`) and Phase 5.5 (`fix-safety-checker`).

This phase runs once per audit, not per iteration. The purposes are stable across iterations; only the file content changes.

---

### Detect

#### Phase 2: Parallel audit dispatch (always)

Read `agents/auditor.md` and use its full content as the prompt for each subagent. Substitute the placeholders (`target_file_path`, `related_files_paths`, `exclusion_list`) with the values collected in Phase 1. The prompt must be **byte-identical** across all N instances — same placeholder substitution, no per-instance variation.

Dispatch all `N` subagents in **one tool-call message** with `run_in_background: true`, `subagent_type: general-purpose`, and `model: "sonnet"`.

Critical requirements:
- All N subagents must be launched in the **same tool-call message** (parallel dispatch)
- Use `run_in_background: true` so the harness notifies you on completion
- **Pass `model: "sonnet"` explicitly for Phase 2 only.** This overrides the general "subagents inherit parent's model" guideline because N=9 parallel auditors with an opus parent would be cost-prohibitive (~200-300k tokens/iteration × up to 5 iterations × opus rate). The HIGH-severity detection along the 7 axes is bounded enough that sonnet's quality suffices, and the ≥threshold aggregation absorbs per-instance noise. Phases 4.5 / 4.6 / 5.5 (single-agent **evaluation** subagents — false-positive filtering, default-redundancy classification, fix safety verdict) must still inherit the parent's model: each runs once with no aggregation buffer, so their judgments need parent-level quality. Only this Phase 2 parallel dispatch is sonnet-locked.
- Do NOT add any "honest opinion" / "no sycophancy" / "be thorough" instruction on top of `agents/auditor.md` — the Forthright Assessment rules in the user's CLAUDE.md already cover this, and extra instructions would bias the audit
- Do NOT modify the 7 axes, output format, or "what not to flag" section in `agents/auditor.md` per-iteration. Touch only the placeholders.

While waiting for completion notifications, draft the aggregation table template in your head so you're ready when results arrive.

#### Phase 3: Aggregate (always)

When each subagent completes, capture its HIGH issues. Once all N have completed, build two tables:

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
| A | … | #1, #3, #5, … | 5/9 | ❌ fix candidate |
| B | … | #2, #4, … | 4/9 | ✅ acceptable (from exclusion list) |
| C | … | #6, #7 | 2/9 | — (below threshold) |

**Aggregation drift hedge**: Do not unilaterally downgrade subagent verdicts. If you (the main thread) believe an issue 4+ instances flagged is actually acceptable, do **not** quietly drop it — surface the disagreement to the user in Phase 4 triage. Explicitly add it to a "main-thread-disputed" list in the report rather than treating it as resolved. Main-thread session context biases toward agreement with the user (sycophancy gradient); subagents read in fresh contexts and their independent judgment is the trust anchor of this skill, not yours. If you find yourself softening a finding because "it doesn't feel like a defect", that's exactly the drift this hedge prevents — leave the call to the user.

#### Phase 4: Triage (always)

For each convergent issue (count ≥ threshold), categorize:

- **Fix candidate**: New reproducible issue not in the exclusion list → propose a fix
- **Acceptable**: Matches an exclusion the user provided → note and skip
- **Below threshold**: count < threshold → note in the table but do not propose a fix

If 0 fix candidates remain, skip Phases 4.5–6 and go directly to Phase 8 (stop condition check) — there is nothing to re-verify in Phase 7 because no fixes were applied this iteration.

#### Phase 4.5: False-positive detection (when fix candidates exist)

Convergent issues can still be wrong — multiple subagents can share a blind spot, anchor on the same misreading, or flag an externally-defined concept as "undefined" when it's actually documented elsewhere. Before drafting fix proposals, spawn a `false-positive-detector` subagent.

Read `agents/false-positive-detector.md` and dispatch one subagent with:
- `target_file`: the audit target path
- `related_files`: any project-level CLAUDE.md, CLAUDE.local.md, settings.json, etc.
- `convergent_issues`: the fix candidates from Phase 4
- `exclusion_list`: the current exclusion list (including any items added during this iteration)

The subagent returns a per-issue verdict (REAL / FALSE / NEEDS_HUMAN). Filter out FALSE issues — they should not become fix proposals. For NEEDS_HUMAN issues, surface them to the user in Phase 5 with the agent's reasoning so the user can decide.

---

### Triage classification

#### Phase 4.6: Default redundancy check (when REAL fix candidates remain)

Long instruction files often contain rules that **duplicate Claude Code's default system prompt or harness defaults**. Refining the wording of a redundant rule wastes effort — the right fix is to compress (keep only the unique portion) or delete the rule entirely. This phase classifies each REAL fix candidate so Phase 5 chooses the right fix shape.

Read `agents/default-redundancy-checker.md` and dispatch one subagent with:
- `target_file`: the audit target path
- `convergent_issues`: REAL fix candidates from Phase 4.5, with the relevant section text (cited line ± 10 lines)
- `section_purposes`: from Phase 1.5

The subagent returns a per-issue classification:
- **KEEP** — rule has unique non-default value; Phase 5 should refine wording
- **SIMPLIFY** — rule partially duplicates defaults; Phase 5 should compress to the unique portion
- **REMOVE** — rule fully covered by defaults; Phase 5 should delete

The subagent hedges toward KEEP when uncertain (asymmetric cost: wrong delete is worse than wrong keep). Trust the classification, but if it returns REMOVE for a rule you (the main thread) believe has unique value, surface the disagreement to the user — same drift-hedge logic as Phase 3.

---

### Fix

#### Phase 5: Fix drafting (when REAL fix candidates remain)

For each REAL fix candidate, draft a fix that matches its Phase 4.6 classification:

- **KEEP** verdict → refine the wording to address the convergent issue
- **SIMPLIFY** verdict → compress the rule to only its unique-value portion (use Phase 4.6's `suggested_action` as a hint)
- **REMOVE** verdict → delete the rule entirely

Read the target file with Read to verify current line numbers and content before drafting.

**Draft mode — single vs. multi-option**

For each fix, decide the drafting mode based on scope:

- **Single-proposal mode** (default): use when the fix is **trivial** — ≤3 lines changed, no structural change, no choice between substantially different approaches. Draft one before/after diff.
- **Multi-option mode**: use when the fix is **substantive** — more than 3 lines changed, OR the fix restructures a rule, OR there's a meaningful choice between approaches (e.g., delete vs. compress vs. keep-with-refinement, or two different wordings with different trade-offs). Draft 2-3 alternative before/after options, each labeled with its trade-off.

The multi-option pattern shifts the decision from "do you agree with my fix?" to "which of these alternatives best fits your intent?" — giving the user more agency on substantive changes without forcing them into free-text Modify each time.

#### Phase 5.5: Fix safety check (before showing each fix to user)

Spawn a `fix-safety-checker` subagent. Read `agents/fix-safety-checker.md` and dispatch one subagent per fix with:
- `target_file`: the audit target path
- `issue_summary`: 1-2 lines describing the convergent issue this fix addresses
- `proposed_fix`: the before/after diff, rationale, and Phase 4.6 classification (KEEP/SIMPLIFY/REMOVE)
- `section_purposes`: from Phase 1.5 (used as the authoritative intent baseline, not re-derived from the file)

For multi-option fixes (Phase 5), dispatch one safety-checker per option — each option gets its own verdict.

The subagent returns a verdict block including `verdict`, `addresses_issue`, `cross_section_impact`, `rule_conflicts`, `intent_preserved`, and `rule_burden_impact` (REDUCES / NEUTRAL / INCREASES_MINOR / INCREASES_MAJOR).

- **SAFE** → present to user
- **UNSAFE** → do NOT present this fix as-is. Re-draft addressing the concerns, or escalate to user with explicit warnings
- **NEEDS_REVIEW** → present to user with trade-offs clearly stated in the AskUserQuestion description
- **`rule_burden_impact: INCREASES_MAJOR`** → regardless of verdict, surface this prominently to the user. Adding rules has real cost.

#### Phase 5.6: User approval per fix

For each fix candidate, present via **AskUserQuestion**. The option structure depends on the drafting mode:

**Single-proposal mode options:**
- Apply this fix
- Skip (add to exclusion list as architectural tension)
- Modify (user provides alternative wording)

**Multi-option mode options:**
- Option A: [first alternative — typically REMOVE or strongest compression, with 1-line trade-off label]
- Option B: [second alternative — typically SIMPLIFY or middle ground]
- Option C: [third alternative — typically KEEP with refinement]
- Skip (add to exclusion list)
- Modify (user provides different wording)

Include trade-off labels in option descriptions — e.g., "Option A: Delete entirely. Trade-off: loses type-annotation guidance" vs. "Option B: Compress to 1 line. Trade-off: keeps the unique value-add, drops the comments overlap." The user should see why each option exists.

Do not batch fix candidates across one question. One AskUserQuestion per fix candidate, so each can be decided independently.

---

### Apply

#### Phase 6a: Apply via Edit (when user approves)

Use **Edit** to apply approved fixes. After all Edit calls, briefly confirm what was applied.

#### Phase 6b: Auto-mode classifier handling (when Edit is blocked)

When the target file is a Claude Code agent config (`~/.claude/CLAUDE.md`, `~/.claude/settings.json`, `~/.claude/settings.local.json`, project `.claude/settings.json`, project `.claude/settings.local.json`, project `CLAUDE.md`, `CLAUDE.local.md`, `.claude/agents/*`, `.claude/skills/*`, `.claude/hooks/*`, `.claude/commands/*`, `.mcp.json`), Edit may be denied by the auto-mode classifier with a reason mentioning **"Self-modification of agent config"**.

This is not a workflow defect. The classifier exists to prevent silent agent self-modification; the AskUserQuestion authorization is the intended unlock mechanism.

Playbook when Edit returns this denial:

1. **Stop. Do not retry blindly** — the classifier needs explicit per-edit user authorization to release.
2. Use **AskUserQuestion** with this template (adapt the target file and edit summary):

   ```
   Question:
     The auto-mode classifier blocked Edit on `<target_file>` as self-modification.
     Proposed change: <1-2 line before → after summary>
     May I apply this Edit to `<target_file>`?

   Options:
     - "Yes, update my <CLAUDE.md / settings.json / etc.>" — explicit per-file authorization
     - "Only update L<line_range>" — scope-limited authorization
     - "Cancel (do not Edit)" — abort this specific fix
   ```

   The "Yes, update my <file>" phrasing matters — the classifier listens for explicit-authorization patterns, not generic agreement. "OK" or "go ahead" may not release the block.

3. After explicit authorization, **retry the exact same Edit call**. The classifier releases for that single retry only; subsequent Edits on the same file need their own authorization.

4. If the retry also fails (rare), surface the error to the user and ask whether to skip the fix or have the user apply it manually.

This playbook applies per-fix, not per-session. Each blocked Edit needs its own authorization.

---

### Verify

#### Phase 7: Re-verify (when iteration < max_iterations and fixes were applied)

Re-dispatch N subagents (same prompt, including updated exclusion list if any were added during Phase 5.6) and repeat Phases 2-4 (and Phase 4.5 + 4.6 if fix candidates re-emerge). Phase 1.5 section purposes are stable across iterations — do not re-collect them unless the user explicitly says the section structure changed.

#### Phase 8: Stop condition check (always after each iteration)

Stop and report final state when **any** of these holds:

| Condition | Interpretation |
|---|---|
| All N instances report "NO HIGH ISSUES" | Full convergence — file is clean |
| ≥3 of N instances report "NO HIGH ISSUES" | Practical convergence |
| HIGH avg plateau for 2 consecutive iterations (avg change < 1) | Structural limit reached — remaining issues are likely architectural tensions |
| iteration ≥ max_iterations | Hard limit — report current state, flag diminishing returns |
| 0 fix candidates from Phase 4 | Nothing actionable left |

Report the iteration history (Phase 3 tables across all iterations) so the user can see the trajectory.

## Audit prompt

The audit prompt lives in `agents/auditor.md`. Phase 2 reads that file and uses its full content as the subagent prompt (with placeholders substituted). The design choices behind the audit prompt — the 7 axes, the "no collusion" framing, the strict HIGH-only filter, the exclusion handling — are documented inline in that file.

Do not duplicate the prompt here. The single source of truth is `agents/auditor.md`. Editing the prompt means editing that file.

## Output format

After all iterations complete, present a final report with this structure:

```
## Audit complete — final report

### Iteration trajectory

| Iteration | HIGH avg | Convergent issues | Fixes applied | Status |
|---|---|---|---|---|
| 1 | 5.6 | 2 | 2 | continued |
| 2 | 2.1 | 0 | 0 | converged (≥3/9 said clean) |

### Fixes applied
- (line range) before → after — 1-sentence rationale
- ...

### Remaining known tensions (carried over to exclusion list)
- ...

### Recommendation
[Specific recommendation based on convergence pattern — e.g., "file is now in good shape", or "consider re-running with relaxed exclusions if you want to re-examine known tensions"]
```

## Tool requirements

| Tool | Use |
|---|---|
| `Agent` | Parallel subagent dispatch (Phase 2 audit, Phase 4.5 false-positive detection, Phase 4.6 default redundancy check, Phase 5.5 fix safety check). Use `run_in_background: true` for Phase 2 (N parallel auditors); Phases 4.5 / 4.6 / 5.5 single-agent dispatches can be foreground since they gate the next phase |
| `Read` | Phase 1.5 (read target file to draft section purposes); verify line numbers before proposing fixes; read `agents/*.md` files when dispatching specialized subagents |
| `AskUserQuestion` | Phase 1 setup, Phase 1.5 section purpose confirmation, Phase 5.6 fix approval, Phase 6b auto-mode classifier authorization — never use plain text questions per CLAUDE.md communication rule |
| `Edit` | Apply approved fixes; if blocked by auto-mode classifier, follow Phase 6b playbook |
| (optional) `TaskCreate` / `TaskUpdate` | Track per-iteration progress for multi-iteration audits |

## Bundled agents

The `agents/` directory contains specialized subagent prompts referenced by specific phases of the workflow. Read the relevant file when dispatching the subagent — pass its content as the prompt body, with any placeholder substitution noted.

| Agent file | Used in | Dispatched | Purpose |
|---|---|---|---|
| `agents/auditor.md` | Phase 2 | N parallel (default 9), `run_in_background: true`, `model: "sonnet"` | Independent HIGH-severity audit along the 7 axes; each instance returns up to 10 findings as a markdown table |
| `agents/false-positive-detector.md` | Phase 4.5 | 1 foreground (parent model inherited) | Independent re-read of each convergent issue to filter shared-blind-spot false positives before fix drafting |
| `agents/default-redundancy-checker.md` | Phase 4.6 | 1 foreground (parent model inherited) | Classifies each REAL fix candidate as KEEP / SIMPLIFY / REMOVE based on whether the rule duplicates Claude Code default behavior |
| `agents/fix-safety-checker.md` | Phase 5.5 | 1 per fix candidate (or 1 per option in multi-option mode), foreground (parent model inherited) | Verifies a proposed fix does not break cross-section references, contradict other rules, or distort intent; also reports rule-burden impact (REDUCES / NEUTRAL / INCREASES_MINOR / INCREASES_MAJOR) |

## Common pitfalls

- **Forgetting the exclusion list** → subagents re-flag intentional design every iteration; convergence never reaches. Always collect exclusions in Phase 1.
- **Skipping Phase 1.5 section purposes** → `fix-safety-checker.intent_preserved` becomes circular (judged by re-reading the section being changed). The phase costs 1 AskUserQuestion; do not skip.
- **Batching all fix proposals into one question** → user gets overwhelmed and either rubber-stamps or rejects everything. Ask one fix at a time.
- **Skipping Phase 7 re-verify** → "I applied 2 fixes, done" is premature. Without re-verification, you don't know if the fixes actually changed convergence behavior.
- **Modifying the audit prompt to "improve" it** → breaks reproducibility. The 7 axes and exclusion section are load-bearing; touch only the placeholders.
- **Dispatching subagents serially (one after another)** → wastes time. Always dispatch all N in one message with `run_in_background: true`.
- **Treating "below threshold" issues as fixable** → ≥4/9 is the bar. Below that, the signal is too noisy to trust.
- **Skipping Phase 4.5 / 4.6 / 5.5 verification subagents** → ≥threshold convergence does not guarantee correctness; multiple subagents can share a blind spot, and the rule itself may be redundant with defaults. The 3 phases catch shared-misreading false positives, redundant rules, and unsafe fixes respectively. All are cheap (1 subagent each) and save the user from approving wrong fixes.
- **Letting Phase 5.5 verdict be overridden silently** → if `fix-safety-checker` returns UNSAFE, do not present that fix to the user unmodified. Either re-draft addressing the concern, or surface the UNSAFE verdict in the AskUserQuestion description so the user makes an informed decision.
- **Main-thread aggregation drift** → quietly downgrading subagent findings during Phase 3 because they "don't feel like defects" defeats the purpose of multi-agent audit. The subagents read in fresh contexts; you read with accumulated session bias. Leave disagreements explicit for the user to resolve.
- **Refining a redundant rule instead of removing it** → if Phase 4.6 returns REMOVE or SIMPLIFY, Phase 5 should not draft a KEEP-style refinement fix. Honor the classification.
- **Using single-proposal mode for substantive fixes** → forcing the user into "Apply / Skip / Modify (free text)" for a fix that has 3 valid alternatives wastes their time. Use multi-option mode when the fix is substantive (>3 lines changed, structural change, or genuine choice between approaches).
- **Retrying auto-mode-blocked Edits blindly** → without explicit AskUserQuestion authorization, the classifier will block every retry. Follow the Phase 6b playbook: stop, ask with the "Yes, update my <file>" template, then retry once authorized.
- **Ignoring `rule_burden_impact: INCREASES_MAJOR`** → adding rules has real cost (context budget, attention dilution, over-cautious behavior). Major increases warrant explicit user scrutiny — surface them in the AskUserQuestion description, do not bury.

## Cost notes

- Each iteration costs roughly `N × (average subagent token usage for one audit)`. A 9-instance audit on a ~120-line CLAUDE.md typically runs 200-300k tokens total per iteration.
- A 5-iteration audit can therefore consume ~1-1.5M tokens. Surface this estimate to the user at Phase 1 so they can decide whether to reduce `N` for cost reasons.
- The cost is justified when the file is high-leverage (loaded into every Claude session) and the defects compound over time. For one-off documents, this skill is overkill.

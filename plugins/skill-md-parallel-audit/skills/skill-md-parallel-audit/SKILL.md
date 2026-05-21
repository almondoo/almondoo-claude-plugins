---
name: skill-md-parallel-audit
description: Multi-agent parallel audit of a SKILL.md file for HIGH-severity quality issues — missing qualifiers, grammar errors, terminology drift, cross-section logical contradictions, implicit premises, incomplete enumerations, and undefined terms. Dispatches N independent subagents to audit the same SKILL.md, aggregates findings by reproducibility (≥4/9 default), distinguishes new fixable issues from known design choices the user has accepted, classifies remaining issues for redundancy against other skills (skill-creator / skill-eval / siblings), and proposes targeted fixes via AskUserQuestion. Use whenever the user asks to audit / review / verify / check the quality / consistency / ambiguity of a SKILL.md file, or mentions "audit a skill", "skill spec review", "skill description ambiguity", "parallel review of SKILL.md", or wants high-confidence reproducibility on what is wrong with their skill specification. Sibling of `claude-md-parallel-audit` (same engine, retuned for SKILL.md targets); distinct from `skill-eval` which scores structural quality and runs A/B benchmarks — this skill specifically finds prose-level defects via convergence of independent auditors.
---

# skill-md-parallel-audit

## Purpose

SKILL.md files accumulate the same subtle defects long instruction files do: missing qualifiers ("read it into a subagent" — how?), terminology drift between sections, implicit premises about placeholder semantics, cross-section logical contradictions (verdict heuristics that contradict downstream script behavior). A single review pass — even careful — misses some defects and over-flags others.

The fix is the same as `claude-md-parallel-audit`'s: dispatch **multiple independent audits in parallel** and treat findings that **multiple auditors flag** as the high-confidence signal. The engine (auditor / false-positive-detector / fix-safety-checker) is shared via file copies under `agents/`. The only SKILL.md-specific addition is `skill-md-redundancy-checker` (Phase 4.6), which asks whether each fix candidate duplicates content already documented in `skill-creator`, `skill-eval`, or a sibling skill — a question that doesn't arise for CLAUDE.md targets.

This skill was validated by running it against `skill-eval/SKILL.md` (N=9, threshold=4): 9/9 auditors converged on 6 distinct defects (5 REAL + 1 NEEDS_HUMAN after Phase 4.5; 1 FALSE positive correctly filtered). The 7-axis taxonomy from `agents/auditor.md` requires no SKILL.md-specific adaptation — the axes ("missing qualifier", "cross-section contradiction", etc.) are file-type agnostic.

## When to use

Trigger this skill when the user:

- Asks to **audit / review / verify / check the quality / ambiguity** of a SKILL.md file
- Wants to find **omissions / inconsistencies / contradictions / coherence issues** in a skill specification
- Mentions **multi-agent audit**, **parallel review**, **convergence audit**, **independent verification** in the context of a skill
- Says the skill spec "feels inconsistent" or "I want a second opinion on this SKILL.md"
- Has just translated a SKILL.md (e.g., JP → EN) and wants to catch translation-induced ambiguity
- Wants to know which SKILL.md issues are **deliberate design choices** vs. **fixable defects**

Do NOT use this skill for:

- Auditing CLAUDE.md / AGENTS.md / GEMINI.md (use sibling `claude-md-parallel-audit` instead)
- Scoring SKILL.md against structural axes / running A/B benchmarks (use `skill-eval` instead — its static + dynamic layers are complementary to this skill's prose audit)
- Authoring a new SKILL.md from scratch (use `skill-creator`)
- Auditing non-SKILL.md files (source code, docs, READMEs)

## Configuration parameters

Defaults shown. The skill should ask the user to confirm or override these at Phase 1.

| Parameter | Default | Description |
|---|---|---|
| `N` | 9 | Number of parallel subagents to dispatch per iteration |
| `threshold` | 4 | Minimum instances that must flag an issue for it to be considered reproducible (≥4/9 ≈ 44%) |
| `max_iterations` | 5 | Hard upper bound on audit→fix→verify cycles |
| `target_file` | (asked) | Absolute path to the SKILL.md to audit (e.g. `plugins/foo/skills/foo/SKILL.md`) |
| `related_files` | (drafted) | Files in `agents/` / `references/` / `scripts/` / `evals/` under the same skill directory — used for cross-reference integrity checks (the orchestrator can glob these) |
| `exclusions` | (asked, with SKILL.md-specific defaults pre-loaded) | Items the user does NOT want re-flagged (see below) |
| `section_purposes` | (drafted then asked in Phase 1.5) | Map from each section heading to its 1-line purpose; established once per audit and reused across iterations |

### SKILL.md-specific exclusion defaults

Pre-load these as suggested exclusions at Phase 1; the user can deselect any that don't apply to their target:

1. **Claude Code official `subagent_type` values** — `general-purpose`, `Explore`, `Plan`, `claude`, plugin-namespaced types like `feature-dev:code-architect`, etc. Auditors who don't have the user's harness context will flag these as "undefined". Match against the list in the user's `~/.claude/CLAUDE.md` or the system-prompt agent-types list.
2. **Placeholder conventions** — `<this-skill-path>` / `<workspace>` / `<target-skill-path>` / `<skill-name>` / `<id>` / `<N>` — these are inline templates that the executor substitutes at runtime, not undefined terms.
3. **Cross-skill references that the SKILL.md author intentionally leaves as informational pointers** — e.g. "see skill-creator's references/schemas.md" where the load-bearing content is also inlined. Distinguish "broken reference" (REAL defect) from "informational pointer" (intentional).
4. **Frontmatter content** — `description` length, trigger phrasing, etc. are owned by `skill-eval`'s static axes; do not re-flag here.

If you have additional intentional design choices (e.g., a specific section is intentionally terse for triggering reasons), add them at Phase 1.

## Workflow

The skill runs in phases grouped as **Setup → Detect → Triage → Fix → Apply → Verify**, identical in structure to `claude-md-parallel-audit`. The phase numbering is preserved so transferred knowledge applies. SKILL.md-specific changes are noted per phase.

---

### Setup

#### Phase 1: Inputs (always)

Use **AskUserQuestion** to collect:

1. **Target SKILL.md path** (absolute; must end in `SKILL.md`)
2. **Confirm N / threshold / max_iterations** (default 9 / 4 / 5)
3. **Exclusions** — present the SKILL.md-specific defaults above as a multi-select with each as a suggested item; let the user deselect any that don't apply, and accept free-text additions for skill-specific intentional design.

If the target path points to a plugin root or a skills directory (not directly to a `SKILL.md`), glob `**/SKILL.md` under it and offer the candidates via AskUserQuestion.

#### Phase 1.5: Section intent baseline (always)

Identical to `claude-md-parallel-audit` Phase 1.5. Read the SKILL.md, draft a 1-line purpose per `## H2` and meaningful `### H3`, present the full batch via AskUserQuestion with options "All purposes look right" / "Some need correction". Store the confirmed map as `section_purposes` and pass it to Phase 4.6 (`skill-md-redundancy-checker`) and Phase 5.5 (`fix-safety-checker`).

This phase runs once per audit, not per iteration.

---

### Detect

#### Phase 2: Parallel audit dispatch (always)

Read `agents/auditor.md` and use its full content as the prompt for each subagent. Substitute the placeholders (`target_file_path`, `related_files_paths`, `exclusion_list`) with the values collected in Phase 1. The prompt must be **byte-identical** across all N instances.

Dispatch all `N` subagents in **one tool-call message** with `run_in_background: true`, `subagent_type: general-purpose`, and `model: "sonnet"`.

Critical requirements:

- Same-message parallel dispatch (not sequential)
- `model: "sonnet"` explicit override of the parent-model inheritance default — Phase 2 sonnet-lock matches `claude-md-parallel-audit`'s cost rationale (~200-300k tokens per N=9 iteration on a typical SKILL.md)
- Phases 4.5 / 4.6 / 5.5 (single-agent evaluation subagents) must inherit the parent's model
- Do NOT add "be honest" / "no sycophancy" instructions on top of `auditor.md` — the user's CLAUDE.md "Forthright Assessment" rules already cover this
- Do NOT modify the 7 axes or output format in `auditor.md`

#### Phase 3: Aggregate (always)

Identical to `claude-md-parallel-audit` Phase 3. Build Table A (per-instance HIGH count) and Table B (convergent issues with count ≥ threshold). Cluster similar findings (same Line + same root cause, even if phrasing differs).

**Aggregation drift hedge**: same as `claude-md-parallel-audit` — if you (the main thread) believe an issue 4+ instances flagged is actually acceptable, surface the disagreement to the user in Phase 4 triage rather than quietly dropping it. Main-thread session context biases toward agreement; subagents read fresh.

#### Phase 4: Triage (always)

Identical to `claude-md-parallel-audit`. For each convergent issue, categorize as fix candidate / acceptable (matches exclusion) / below threshold. If 0 fix candidates remain, skip Phases 4.5–6 and go directly to Phase 8 (stop condition check).

#### Phase 4.5: False-positive detection (when fix candidates exist)

Read `agents/false-positive-detector.md` and dispatch one subagent with `target_file`, `related_files`, `convergent_issues`, `exclusion_list`. Filter REAL / FALSE / NEEDS_HUMAN per the agent's verdict.

For SKILL.md targets, common shared-blind-spot false positives:

- Auditors flag `subagent_type: general-purpose` as undefined → FALSE (covered by SKILL.md-specific exclusion default 1)
- Auditors flag `<this-skill-path>` as undefined → FALSE (covered by SKILL.md-specific exclusion default 2)
- Auditors flag a cross-skill schema reference as "unverifiable" → REAL only if the load-bearing content is not also inlined

---

### Triage classification

#### Phase 4.6: Skill redundancy check (when REAL fix candidates remain)

Read `agents/skill-md-redundancy-checker.md` and dispatch one subagent with:

- `target_file`: the audit target SKILL.md path
- `convergent_issues`: REAL fix candidates from Phase 4.5
- `section_purposes`: from Phase 1.5
- `sibling_skills`: list of installed skills the audit target should not duplicate. At minimum include `skill-creator` (the official skill-authoring skill) and any other skills in the same marketplace that document overlapping concepts. The orchestrator can glob `plugins/*/skills/*/SKILL.md` of the marketplace and pass their `name` + `description` as the candidate list.

The subagent returns KEEP / SIMPLIFY / REMOVE per issue, with `suggested_action` for SIMPLIFY/REMOVE.

This phase replaces `claude-md-parallel-audit`'s `default-redundancy-checker`. The question "is this redundant with Claude Code defaults?" rarely applies to SKILL.md — the relevant question for SKILL.md is "is this redundant with another skill the reader is expected to know about?".

The subagent hedges toward KEEP when uncertain (asymmetric cost: wrong delete is worse than wrong keep). If it returns REMOVE for a rule you believe has unique value, surface the disagreement to the user.

---

### Fix

#### Phase 5: Fix drafting (when REAL fix candidates remain)

Identical to `claude-md-parallel-audit` Phase 5. KEEP → refine wording, SIMPLIFY → compress to unique portion, REMOVE → delete (+ optional 1-line pointer per `skill-md-redundancy-checker`'s `suggested_action`).

Single-proposal mode vs multi-option mode rule: same as `claude-md-parallel-audit` (≤3 lines, no structural change → single; substantive → multi-option with trade-off labels).

#### Phase 5.5: Fix safety check (before showing each fix to user)

Read `agents/fix-safety-checker.md` and dispatch one subagent per fix (or per option in multi-option mode). The checker verifies cross-section references, rule conflicts, and intent preservation against the Phase 1.5 `section_purposes` baseline.

For SKILL.md targets, watch specifically for:

- **Placeholder cross-references** — if a fix changes a placeholder name (e.g., `<workspace>` semantics), every other occurrence of the placeholder in the same SKILL.md must remain valid.
- **Script schema drift** — if the fix changes wording that documents a script's input/output schema, verify against the actual script (`scripts/*.py` in the same skill directory).
- **eval-axes / references doc drift** — if the SKILL.md has a `references/eval-axes.md` or similar rationale doc, a fix to a SKILL.md table may require synchronized edits to the references doc.

The fix-safety-checker's NEEDS_REVIEW verdict is informative and not a blocker — the user can override after seeing the trade-offs.

#### Phase 5.6: User approval per fix

Identical to `claude-md-parallel-audit` Phase 5.6. One AskUserQuestion per fix candidate. Options match the drafting mode (Apply / Skip-as-exclusion / Modify for single; Option A / B / C / Skip / Modify for multi-option).

---

### Apply

#### Phase 6: Apply via Edit

Use **Edit** to apply approved fixes. SKILL.md files do NOT typically trip the auto-mode classifier ("Self-modification of agent config") because they are plugin artifacts, not Claude Code's own config files. If a fix would synchronize a script (e.g., `render_report.py`) or a references doc in the same skill, apply those Edits as part of the same approved fix — Phase 5.5's verdict scope covers same-PR follow-ups.

After all Edit calls, briefly confirm what was applied (file list + 1-line description per fix).

---

### Verify

#### Phase 7: Re-verify (when iteration < max_iterations and fixes were applied)

Re-dispatch N subagents (same prompt, with updated exclusion list if any were added in Phase 5.6) and repeat Phases 2–4 (and 4.5 / 4.6 if fix candidates re-emerge). Phase 1.5 section purposes are stable across iterations — do not re-collect them unless the user explicitly says the section structure changed.

#### Phase 8: Stop condition check (always after each iteration)

Identical to `claude-md-parallel-audit` Phase 8:

| Condition | Interpretation |
|---|---|
| All N instances report "NO HIGH ISSUES" | Full convergence — SKILL.md is clean |
| ≥3 of N instances report "NO HIGH ISSUES" | Practical convergence |
| HIGH avg plateau for 2 consecutive iterations (avg change < 1) | Structural limit reached — remaining issues are likely deliberate design |
| iteration ≥ max_iterations | Hard limit — report current state, flag diminishing returns |
| 0 fix candidates from Phase 4 | Nothing actionable left |

Report the iteration history (Phase 3 tables across all iterations) so the user can see the trajectory.

## Audit prompt

The audit prompt lives in `agents/auditor.md` (copy of `claude-md-parallel-audit`'s; the 7 axes are file-type agnostic and validated for SKILL.md by the cross-test described in Purpose). Phase 2 reads that file and uses its full content as the subagent prompt (with placeholders substituted).

Do not duplicate the prompt here. Editing the prompt means editing that file.

## Output format

After all iterations complete, present a final report with the same structure as `claude-md-parallel-audit`:

```
## Audit complete — final report

### Iteration trajectory

| Iteration | HIGH avg | Convergent issues | Fixes applied | Status |
|---|---|---|---|---|
| 1 | 7.7 | 6 | 1 | continued |
| 2 | 2.1 | 0 | 0 | converged (≥3/9 said clean) |

### Fixes applied
- (line range) before → after — 1-sentence rationale

### Remaining known design choices (carried over to exclusion list)
- ...

### Recommendation
[Specific recommendation based on convergence pattern]
```

## Tool requirements

| Tool | Use |
|---|---|
| `Agent` | Parallel subagent dispatch (Phase 2, 4.5, 4.6, 5.5). `run_in_background: true` for Phase 2; single-agent dispatches can be foreground |
| `Read` | Phase 1.5 (draft section purposes); verify line numbers before fix drafting; read `agents/*.md` when dispatching subagents |
| `AskUserQuestion` | Phase 1 setup, Phase 1.5 section purpose confirmation, Phase 5.6 fix approval — never use plain text questions |
| `Edit` | Apply approved fixes |
| `Glob` | Phase 1 SKILL.md candidate discovery (when user passes a plugin root); Phase 4.6 sibling-skill discovery |
| (optional) `TaskCreate` / `TaskUpdate` | Track per-iteration progress |

## Bundled agents

| Agent file | Used in | Dispatched | Purpose |
|---|---|---|---|
| `agents/auditor.md` | Phase 2 | N parallel (default 9), `run_in_background: true`, `model: "sonnet"` | Independent HIGH-severity audit along 7 axes; returns up to 10 findings as a markdown table. **Copy** of `claude-md-parallel-audit`'s; do not diverge without justification — the axes are file-type agnostic |
| `agents/false-positive-detector.md` | Phase 4.5 | 1 foreground (parent model) | Independent re-read of each convergent issue to filter shared-blind-spot false positives. **Copy** of `claude-md-parallel-audit`'s |
| `agents/skill-md-redundancy-checker.md` | Phase 4.6 | 1 foreground (parent model) | Classifies each REAL fix candidate as KEEP / SIMPLIFY / REMOVE based on whether the rule duplicates skill-creator, skill-eval, or a sibling skill. **SKILL.md-specific**; replaces `claude-md-parallel-audit`'s `default-redundancy-checker` |
| `agents/fix-safety-checker.md` | Phase 5.5 | 1 per fix candidate (or 1 per option), foreground | Verifies a proposed fix does not break cross-section references, contradict other rules, or distort intent. **Copy** of `claude-md-parallel-audit`'s |

## Common pitfalls

- **Forgetting to enable the SKILL.md-specific exclusion defaults** → auditors will re-flag `subagent_type: general-purpose` and `<this-skill-path>` every iteration; convergence stalls
- **Skipping Phase 4.6 (skill-redundancy)** → Phase 5 defaults to KEEP for every fix candidate, refining wording on rules that should instead link to skill-creator/skill-eval and be deleted
- **Editing `agents/auditor.md` to be "SKILL.md-specific"** → the 7 axes are file-type agnostic and divergence breaks the engine-sharing rationale. If you find yourself wanting to add a SKILL.md-specific axis, propose it upstream in `claude-md-parallel-audit` instead so the sibling stays in sync
- **Confusing this skill with `skill-eval`** → skill-eval scores structure + runs A/B benchmarks; this skill finds prose defects via multi-agent convergence. The two are complementary, not substitutes
- **Treating cross-skill references as automatic defects** → if the SKILL.md inlines the load-bearing content AND points to the canonical source as a courtesy, that is not a defect. Only "the load-bearing content is only available externally with no resolution path" is REAL

## Cost notes

- One N=9 iteration on a ~300-line SKILL.md typically runs ~200-300k tokens (auditors at sonnet ≈ 30k each × 9 + Phase 4.5/4.6/5.5 verifiers at parent model ≈ 30-50k each)
- A 5-iteration audit can consume ~1-1.5M tokens. Surface this at Phase 1
- The cost is justified when the SKILL.md is high-leverage (triggered frequently, drives downstream subagent behavior) and the defects compound over time. For a 50-line SKILL.md, run with N=3 / threshold=2 instead

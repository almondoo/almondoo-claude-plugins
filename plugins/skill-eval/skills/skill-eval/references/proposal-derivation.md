# Proposal Derivation — guide for the "Top issues to fix" section

After Step 6 confirms the verdict, the "Top issues to fix" section of `report.md` is **hand-written**. The scaffold (`render_report.py`) only places a placeholder — choosing which fixes to surface and how to rank them is a judgment made at hand-write time.

This reference answers:

- which sources to pull fixes from
- how to assign priority (without overfitting)
- how to filter out false positives
- what counts as a "good" fix (with examples)

The design inherits the Category × Priority schema from `agents/analyzer.md` in Anthropic's official `skill-creator`, and extends it with the four sources that are specific to skill-eval (static + dynamic + dogfooding).

---

## 1. Four sources to draw fixes from

### Source A: static FAIL / warn
- List every `passed=false` entry in `static.json`, ordered by severity (`hard_fail` → `warn` → `info`).
- The corresponding fix category is typically `structure` (frontmatter / line count / progressive disclosure) or `instructions` (description triggerability).
- Caveat: `static_check.py` measures only syntactic and quantitative axes. Do not conclude Ship-ready from this source alone — always pair with Source D.

### Source B: the flip side of differentiating assertions
For each assertion in the dynamic layer where `with_skill − without_skill ≥ 0.5`, read it in both directions:

| Observation | Meaning | Action |
|---|---|---|
| Only `with_skill` passes | The skill encoded a contract that without-skill cannot reproduce | If that contract is not yet explicit in `SKILL.md`, add it → `instructions` |
| Only `without_skill` passes | The skill is mis-steering the model | Remove the corresponding MUST / forced step → `instructions` / `examples` |

Verify each observation against the **transcript**, not just the output. Cross-check `grading.json` evidence with the subagent's text response: did the contract truly take effect, or did the format happen to align by chance? If the latter, do not draw a fix from Source B.

### Source C: time / token / variance anomalies
Inspect `run_summary` in `benchmark.json`:

| Observation | Interpretation | Category |
|---|---|---|
| `time delta ≥ 2×`, or `with_skill slower than without` | Skill body is bloated (compression candidate) | `structure` |
| `tokens delta ≥ +50%` | Same, plus possibly `instructions` simplification | `structure` / `instructions` |
| `variance > mean × 0.3` (when `n ≥ 3`) | Flaky instructions inside the skill, or the eval prompt itself is unstable | `instructions`, or an assertion rework |

**Caveat**: if `with_skill` is *faster* than `without_skill` (as in iteration-6 with `time delta = −25s`), that is the opposite signal — likely without-skill spent time "giving up on producing `report.md`". This is not an improvement opportunity on the skill side, so do not draw a fix from Source C.

### Source D: dogfooding gap (axes static_check cannot see)
LEARNINGS.md and the multi-angle review repeatedly surface five axes that `static_check.py` **cannot detect in principle**. Cover them with a human reviewer or an LLM grader. Representative signals for each axis:

| Axis | Typical signal |
|---|---|
| Writing quality | The same point restated in different wording across multiple places / 51-word run-on sentences / translation seams |
| Placeholder resolution | Tokens like `<this-skill-path>` appear on first use without a defined resolution path |
| Translation ambiguity | JP→EN artifacts: shifted prepositions / articles / asymmetric examples |
| Internal consistency | Numbers (thresholds / caps) inside SKILL.md contradict one another |
| Script ↔ doc drift | Examples in SKILL.md (e.g., argument signatures) diverge from the actual `scripts/` |

The category is usually `instructions` (writing-side issues) or `references` (script-doc drift).

---

## 2. How to assign priority

**The single axis is the outcome-changing counterfactual.** This is taken directly from `agents/analyzer.md` L77-184 in `skill-creator`:

| Priority | Condition |
|---|---|
| **high** | Without this fix, the next iteration's benchmark numbers (pass_rate / verdict / differentiating count) would have moved |
| **medium** | The fix improves quality, but it is unclear whether win/loss would flip |
| **low** | Marginal polish (long-tail) |

### What NOT to use as a priority axis

- **Effort-based ranking**: "It's easy, so high" invites overfit. Example: "Fix the typo on L201 → high" promotes a fix that does not actually move the benchmark.
- **Subjective importance**: Rater drift makes it unreproducible between sessions.
- **Everything is high**: The priority signal collapses; you might as well have no priority.
- **Eval-N-specific patches**: A fix tailored to eval-1's particular prompt does not generalize (skill-creator L298).

---

## 3. Yellow flags (low-cost mechanical scan)

Before hand-writing, sweep `SKILL.md` with grep. These are low-effort checks that catch nothing earth-shattering on their own (mostly `low` / `medium` priority), but they should never be missed:

| Pattern | What to check |
|---|---|
| `\b(MUST\|NEVER\|ALWAYS)\b` in all caps | Is the *why* explained? (skill-creator L302 "yellow flag") |
| `<this-skill-path>` / `<workspace>` etc. | Is the resolution explained in the "Placeholders" subsection of "Inputs"? |
| References to `references/X.md` | Does the file exist, and is it linked in proper markdown form `](references/X.md)`? |
| Numeric thresholds (e.g., `≥ 0.5`, `≤ 6`, `1536 chars`) | Is the source or rationale stated nearby? |
| Translation seams (unnatural prepositions / articles from JP→EN) | Re-read the sentence in question |

Mechanical Yellow-flag checks are more reproducible than LLM-derived subjective judgment — any session that runs the scan reaches the same result.

---

## 4. Detecting superficial-pass

A concept lifted from `agents/grader.md` L88-98 in `skill-creator`. Even if an assertion technically passes, do **not** draw a fix from Source B if any of the following hold:

- The evidence is purely formal (e.g., "the filename exists but its content is empty")
- The pass came from a format match rather than a correct reason
- The same assertion would also pass on an obviously wrong output → the assertion itself is invalid

In that case, the proposal should record `source = assertion_rework` and use category `examples` (revise the eval prompt). Priority is **high** because the measurement itself is broken — left unaddressed, every subsequent iteration is noise.

---

## 5. Output schema for a fix proposal

Each fix has **two layers**: a machine-facing metadata header and a human-facing narrative body. The metadata stays for grep / cross-iteration tracking; the body is what the reader actually reads.

### 5.1 Metadata header (machine-facing)

```json
{
  "rank": 1,
  "category": "instructions",
  "priority": "high",
  "source": "differentiating",
  "estimated_effort": "30 min"
}
```

`category` follows the skill-creator enum: `instructions / tools / examples / error_handling / structure / references`. `source` is one of the four listed in this document plus `assertion_rework`, giving five total values. Render this as a single line of mono micro-text, never as the body opener.

### 5.2 Narrative body (human-facing, four blocks)

The reader needs to know **what was wrong, why it matters, what to change to, and how the next iteration will know it worked** — in that order. Do not lead with `rank=1 / category=...` jargon. Render each fix as four labeled blocks:

| Block | Label | Content |
|---|---|---|
| 1 | **Problem** | One short paragraph stating the symptom an iteration would observe: a concrete pass-rate, an actual log line, a file path that exists / does not exist. Cite the evidence (eval id, run number, file path). Avoid abstract verbs like "is unclear" — say *what* an executor did wrong. |
| 2 | **Before** | The current text / behavior. If it is a SKILL.md / config edit, quote the literal lines that are wrong. If it is a behavior issue, describe what the executor actually does today. Bias to literal quotes over paraphrase. |
| 3 | **After** | The proposed text / behavior. Mirror the Before block's shape — if Before is a quote, After is the rewritten quote; if Before is a behavior description, After is the new behavior description. The diff between Before and After is the entire value of the fix. |
| 4 | **Verifiability** | One-sentence checkable hypothesis about what the next iteration's numbers will show. `with_skill pass_rate on eval-N goes 0 → ≥0.5`, `token mean drops by 3000`, `differentiating-assertion count rises from 6 to 8`. Without this line, the fix cannot be evaluated. |

A fix is rejected if any of the four blocks cannot be filled in concretely. Vague problems make vague fixes that no one can verify.

Note: when the report is written in a non-English language (per the report-language policy in skill-eval `SKILL.md`), the block labels are translated into that language. The renderer (`scripts/render_html.py`) accepts both English and translated label variants when parsing fixes back out of `report.md`; the accepted translations live in the viewer's `LOCALES` table. The English form is the canonical authoring style for reference docs in this repository.

### 5.3 Why the schema split

The metadata header keeps the tagging machinery intact (someone can still grep `priority=high` to count blocking items across iterations). The four-block body keeps the reader oriented: a stakeholder who has never seen `category=instructions` can still read the proposal and act on it. Mixing the two — leading with `rank=1 / category=instructions / priority=high / source=anomaly` — looks technical but communicates nothing the metadata header does not already carry.

---

## 6. Examples (good vs. bad)

### Good fix (high, outcome-changing, generalizes)

```
metadata: rank=1 / category=instructions / priority=high / source=differentiating / effort=30 min

Problem
  All six differentiating assertions in iteration-6 belonged to the output-
  contract family (report file existence / verdict label / schema
  conformance). without_skill invented its own schema and failed the
  assertions (eval-1 scores.json instead of static.json; eval-3 omitted the
  hard_fail field entirely). The skill's own SKILL.md never states the
  output contract in one place, so even with_skill executors fall back on
  the dispatch template instead.

Before
  SKILL.md Step 6 says "scaffolds report.md from static.json and
  benchmark.json" — no mention of the canonical file names or schema.
  The contract lives implicitly in `scripts/render_report.py`.

After
  Add an "Output artifacts" subsection under Step 6:
    - canonical file names: `static.json`, `benchmark.json`, `report.md`
    - canonical static.json keys: `target / score / hard_fail / warnings / checks[]`
    - canonical report.md sections: Verdict / Static / Dynamic / Top fixes

Verifiability
  In iteration-7, add assertion `benchmark.json exists` to all three evals.
  Expectation: with_skill pass rate stays at 1.0, without_skill drops to
  ~0.0, lifting the dynamic pass_rate delta from +0.50 to ≥+0.65.
```

### Bad fix #1 (overfit)

```
title: "When eval-1 targets skill-eval-viewer, list the exact files to
        load in Step 3"
```

Rejected: it only works for one specific eval prompt. Falls under
"fiddly overfitty changes" (skill-creator L298).

### Bad fix #2 (priority inflated)

```
priority: high
title: "Fix the typo on L201 ('fail' → 'fails')"
```

Rejected: does not change the outcome (benchmark numbers do not move).
Demote to `low` or drop.

### Bad fix #3 (no source)

```
priority: high
source: (empty)
title: "Tell the report to use more tables, since they look better"
rationale: It feels like it would improve things
```

Rejected: not anchored to any of the four sources. Either fill in the
prior evidence that led to this judgment, or drop.

---

## 7. Two-stage false-positive filter

Borrowed from the multi-stage filtering pattern used in the local audit plugins (`claude-md-parallel-audit` / `skill-md-parallel-audit`). After enumerating candidates from the four sources, apply both stages to each candidate:

1. **Duplication check**: Is the same content already written in `SKILL.md` / `references/` / `LEARNINGS.md`? If yes, treat it as "implementation pending" (promote a LEARNINGS open follow-up into actual implementation) rather than counting it as a new fix.
2. **Neighbor-task counter-evidence**: Identify any eval for which applying the fix would make things worse. For example, "make it more concise" might erase necessary edge-case explanations.

Only candidates that survive both stages are eligible for the Top fix list.

---

## 8. Iteration strategy

- **At most 3 Top fixes per iteration**. More invites overfit plus cognitive load and makes it impossible to isolate which fix actually worked between iterations.
- The remainder belongs in the open follow-ups list at the bottom of `LEARNINGS.md`. They remain candidates in subsequent iterations.
- If the same fix is judged `medium` or below for **two consecutive iterations**, record it as **deliberately rejected** (move it to a "proposals rejected and why" section in `LEARNINGS.md`). Making the rejection explicit prevents reproducibility from quietly degrading.

---

## References

- skill-creator `agents/analyzer.md` (Category × Priority schema, outcome-changing principle)
- skill-creator `agents/grader.md` L88-98 (superficial-pass)
- `claude-md-parallel-audit` / `skill-md-parallel-audit` (multi-stage filtering pattern)
- `docs/learnings/<plugin>.md` at the marketplace repo root (history of accepted and rejected proposals across iterations; lives outside `plugins/` so it is not distributed when the plugin is installed)

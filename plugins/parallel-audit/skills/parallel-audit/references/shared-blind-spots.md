# shared-blind-spots

Target-type-agnostic shared content. Loaded by the main thread at Phase 2 **in addition to** the target-specifics document (`claude-md-specifics.md` or `skill-md-specifics.md`). Each target-specifics document carries its own target-specific entries; this file carries the entries that apply equally to both target types so they live in exactly one place and cannot drift between the two specifics files.

Currently owns two shared layers:

- **Shared exclusion defaults** — pre-loaded into the Phase 2 exclusion list alongside the target-specifics defaults.
- **Shared known-FP patterns** — passed to Phase 6.5 (`false-positive-detector`) as part of the `known_fp_patterns` union.

## When to consult this file

Read this file at Phase 2 right after the target-specifics document. The main thread:

1. Merges the **Shared exclusion defaults** below with the target-specifics document's "Exclusion defaults" list to produce the single pre-loaded exclusion list shown to the user.
2. Merges the **Shared known-FP patterns** below with the target-specifics document's "Common shared-blind-spot patterns" list to produce `known_fp_patterns`, passed unchanged to every Phase 6.5 dispatch.

The orchestrator (main thread) Reads this file. Phase 6.5 (`false-positive-detector`) does NOT Read either specifics file or this one — it receives `known_fp_patterns` as a pre-assembled input, so the union assembly happens once at Phase 2 and is reused across iterations.

## Shared exclusion defaults

Pre-load these as suggested exclusions at Phase 2, regardless of `target_type`. The user can deselect any that don't apply.

- **Claude Code official `subagent_type` values** — `general-purpose`, `Explore`, `Plan`, `claude`, and plugin-namespaced types like `feature-dev:code-architect`. Auditors that lack the user's harness context will flag these as "undefined". The user's `~/.claude/CLAUDE.md` or the harness's system-prompt agent-types list documents them externally; instruction files legitimately depend on them without re-defining them. Applies to both `claude-md` and `skill-md` targets — neither target type defines `subagent_type` itself, both legitimately consume it.

## Shared known-FP patterns

- **Auditors flag the practical-convergence row `(N − threshold + 1)` as "missing rationale"** → FALSE. The derivation is inlined at SKILL.md Phase 12 "Derivation" note. If the auditor read the file in full they had the rationale and missed it. Applies to both `claude-md` and `skill-md` targets because the practical-convergence stop condition is the same formula for both.
- **Auditors flag `subagent_type: general-purpose` (or any other Claude Code official `subagent_type` value) as undefined** → FALSE (covered by the Shared exclusion default above). Applies to both target types because both rely on `subagent_type` as an external Claude Code concept without re-defining it.

## Why this file exists

Previously the `(N − threshold + 1)` entry was duplicated verbatim across `claude-md-specifics.md` and `skill-md-specifics.md`. Architecturally each target-specifics file needed access to the hint, but byte-identical duplication with no automated sync would let the two copies drift on the next edit. Factoring shared entries to this file plus loading-both at Phase 2 gives Phase 6.5 the same coverage with one canonical source.

The Shared exclusion defaults section and the second Shared known-FP pattern (`subagent_type` values) were factored in by the same logic: both specifics files carried byte-similar text for the `subagent_type` exclusion default and its accompanying FP-pattern row. At present this is the single shared exclusion default; future factor-outs will join it here as more shared patterns emerge.

If a new shared pattern emerges (e.g., another formula or terminology choice that auditors keep flagging on both target types), add it here rather than in either target-specifics document. Add it to the target-specifics document **only when** the pattern is genuinely target-specific.

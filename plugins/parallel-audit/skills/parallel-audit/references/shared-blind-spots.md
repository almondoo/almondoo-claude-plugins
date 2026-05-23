# shared-blind-spots

Target-type-agnostic shared-blind-spot patterns. Loaded by the main thread at Phase 2 **in addition to** the target-specifics document (`claude-md-specifics.md` or `skill-md-specifics.md`). Each target-specifics document carries its own target-specific entries; this file carries the entries that apply equally to both target types so they live in exactly one place and cannot drift between the two specifics files.

## When to consult this file

Read this file at Phase 2 right after the target-specifics document. The main thread passes its content as additional context to Phase 6.5 (`false-positive-detector`) so the FP-detector can recognize convergent issues that match a known cross-target shared blind spot.

The orchestrator should treat the union of (target-specifics entries) and (this file's entries) as the full known-FP set for the audit.

## Patterns

- **Auditors flag the practical-convergence row `(N − threshold + 1)` as "missing rationale"** → FALSE. The derivation is inlined at SKILL.md Phase 12 "Derivation" note. If the auditor read the file in full they had the rationale and missed it. Applies to both `claude-md` and `skill-md` targets because the practical-convergence stop condition is the same formula for both.

## Why this file exists

Previously the `(N − threshold + 1)` entry was duplicated verbatim across `claude-md-specifics.md` and `skill-md-specifics.md`. Architecturally each target-specifics file needed access to the hint (Phase 6.5 reads only the target-relevant specifics), but byte-identical duplication with no automated sync would let the two copies drift on the next edit. Factoring shared entries to this file plus loading-both at Phase 2 gives Phase 6.5 the same coverage with one canonical source.

If a new shared pattern emerges (e.g., another formula or terminology choice that auditors keep flagging on both target types), add it here rather than in either target-specifics document. Add it to the target-specifics document **only when** the pattern is genuinely target-specific.

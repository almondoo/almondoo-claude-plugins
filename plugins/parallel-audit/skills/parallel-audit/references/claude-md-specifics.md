# claude-md-specifics

Target-type-specific reference for `target_type == "claude-md"`. Loaded by the main thread at Phase 2 after target type is detected. Owns: exclusion defaults, common shared-blind-spot patterns, and the auto-mode classifier playbook for Phase 11.

This file applies to all CLAUDE.md-family targets: `CLAUDE.md`, `CLAUDE.local.md`, `AGENTS.md`, `GEMINI.md`.

## Exclusion defaults

Pre-load these as suggested exclusions at Phase 2. The user can deselect any that don't apply to their target.

For the **Claude Code official `subagent_type` values** exclusion (previously item 1 here), see `references/shared-blind-spots.md` — it now lives there as a shared exclusion default because both target types need it. The orchestrator merges it into the pre-loaded list at Phase 2.

1. **Documented overrides** — when the file explicitly says "we override the default of X with Y" (e.g., "Phase 4 sonnet-lock overrides the parent-model inheritance default"), auditors sometimes flag this as a CLAUDE.md violation. The override is documented in the file itself; it is intentional.
2. **Dual-layer designs** — when a CLAUDE.md describes a setup where the harness physically blocks something but CLAUDE.md additionally constrains it (e.g., `find` / `grep` allowed by `permissions.allow` but forbidden by CLAUDE.md text), auditors sometimes flag this as contradictory. It is a deliberate defense-in-depth pattern.
3. **Tier rules with dual management** — Tier 3 in the user's CLAUDE.md is enforced by both `permissions.deny` (harness layer) and Claude's self-imposed discipline (Claude layer). This duality is intentional; auditors that flag it as "single source of truth violation" are misreading.
4. **External Claude Code concepts** — `permissions.deny`, `Read tool`, `BashOutput`, `EnterPlanMode`, etc. These are documented in official Claude Code docs; the file legitimately depends on them without re-defining.

The user can add additional intentional design choices at Phase 2 — e.g., "the '1-horsepower cap' metaphor is intentional even if it looks unusual" or "the 'English Feedback' section is intentionally omitted".

## Common shared-blind-spot patterns

Phase 6.5 `false-positive-detector` should be aware of these patterns for CLAUDE.md targets:

- **Auditors flag a documented override as a CLAUDE.md violation** → FALSE (covered by exclusion default 1)
- **Auditors flag dual-layer enforcement as redundancy / contradiction** → FALSE (covered by exclusion defaults 2 and 3)
- **Auditors flag a rule citing `permissions.deny` as "undefined term"** → FALSE (covered by exclusion default 4)

For the **`subagent_type: general-purpose`** FP pattern (previously listed here), see `references/shared-blind-spots.md` — it now lives there with the matching shared exclusion default.

For target-type-agnostic patterns that apply equally to claude-md and skill-md targets (e.g., the `(N − threshold + 1)` "missing rationale" pattern), see `references/shared-blind-spots.md`. Phase 6.5 should treat that file's entries plus the entries above as one combined known-FP set.

## Phase 11 auto-mode classifier playbook

When the target file is a Claude Code agent config, Edit may be denied by the auto-mode classifier with a reason mentioning **"Self-modification of agent config"**. This is not a workflow defect — the classifier exists to prevent silent agent self-modification, and the AskUserQuestion authorization below is the intended unlock mechanism.

### Files that trip the classifier

- `~/.claude/CLAUDE.md`
- `~/.claude/settings.json`
- `~/.claude/settings.local.json`
- Project `.claude/settings.json`
- Project `.claude/settings.local.json`
- Project `CLAUDE.md`
- Project `CLAUDE.local.md`
- `.claude/agents/*`
- `.claude/skills/*` (installed skills, not plugin source)
- `.claude/hooks/*`
- `.claude/commands/*`
- `.mcp.json`

### Playbook (when Edit returns this denial)

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

## Phase 2.5 / 11.5(c) — not applicable

The `skill-eval` static-check integration applies only to `target_type == "skill-md"`. For `claude-md` targets, Phase 2.5 is skipped and Phase 11.5 runs only (a) [re-dispatch audit] and optionally (b) [A/B benchmark — see `references/ab-testing.md`].

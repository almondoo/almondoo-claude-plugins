# skill-md-specifics

Target-type-specific reference for `target_type == "skill-md"`. Loaded by the main thread at Phase 2 after target type is detected. Owns: exclusion defaults, common shared-blind-spot patterns, `skill-eval` integration for Phase 2.5 and Phase 11.5(c), and Phase 11 location-aware classifier guidance.

## Exclusion defaults

Pre-load these as suggested exclusions at Phase 2. The user can deselect any that don't apply.

1. **Claude Code official `subagent_type` values** — `general-purpose`, `Explore`, `Plan`, `claude`, and plugin-namespaced types like `feature-dev:code-architect`. Auditors that lack the user's harness context will flag these as "undefined". Match against the list in the user's `~/.claude/CLAUDE.md` or the system-prompt agent-types list.
2. **Placeholder conventions** — `<this-skill-path>`, `<workspace>`, `<target-skill-path>`, `<skill-name>`, `<id>`, `<N>`. These are inline templates that the executor substitutes at runtime, not undefined terms.
3. **Cross-skill references that the SKILL.md author intentionally leaves as informational pointers** — e.g. "see skill-creator's references/schemas.md" where the load-bearing content is also inlined. Distinguish "broken reference" (REAL defect, no resolution path) from "informational pointer" (intentional courtesy).
4. **Frontmatter content** — `description` length, trigger phrasing, etc. are owned by `skill-eval`'s static axes; do not re-flag here. If Phase 2.5 ran and produced a static.json, append a 5th exclusion item with this literal text:

   > Structural defects already flagged by skill-eval static_check are out of scope for this audit — see `<workspace>/iteration-0/static.json` for the per-axis results. Auditors that want to verify a specific axis Read the file path; do not re-flag axes covered by the static_check.

The user can add skill-specific intentional design at Phase 2 — e.g., "this section is intentionally terse for triggering reasons" or "this skill intentionally duplicates a sibling's rule because the sibling is not always installed".

## Common shared-blind-spot patterns

Phase 6.5 `false-positive-detector` should be aware of these patterns for SKILL.md targets:

- **Auditors flag `subagent_type: general-purpose` as undefined** → FALSE (covered by exclusion default 1)
- **Auditors flag `<this-skill-path>` / `<workspace>` as undefined** → FALSE (covered by exclusion default 2)
- **Auditors flag a cross-skill schema reference as "unverifiable"** → REAL only if the load-bearing content is not also inlined; FALSE if it's an informational pointer (exclusion default 3)
- **Auditors flag frontmatter description as "too long / too short"** → FALSE (exclusion default 4; skill-eval owns this)
- **Auditors flag the cost-tier table as "missing the deep tier rationale"** → KNOWN ASYMPTOTE; the per-tier when-to-use column already documents the rationale, but auditors keep wanting a separate "why these tiers" paragraph

## Phase 2.5: Pre-audit static check

Before the main audit, run `skill-eval`'s `static_check.py` on the target SKILL.md.

### Purpose (three roles)

1. **Hard-fail gate** — if the static check returns `hard_fail: true` (e.g., missing frontmatter, invalid YAML), abort the audit and surface the static evidence to the user. Multi-agent prose audit on a structurally broken SKILL.md wastes tokens.
2. **De-duplicates work** — the static axes (frontmatter validity, body line count, MUST/NEVER density, emoji, progressive disclosure, reference integrity) cover the structural domain. Pre-running and passing the `static.json` to Phase 4 auditors via the exclusion list hardens the delegation: auditors get the static result as context and explicitly do not re-flag those axes.
3. **Calibrates Phase 2 defaults** — if the static check reports a short body (≤100 lines), suggest reducing `N` (e.g., `N=3` already the default, but tell the user prose-defect surface is small). If body is long (>500 lines), keep defaults but flag potential cost (>500k tokens per iteration even at N=3).

### Command shape

```bash
python3 <skill-eval-path>/scripts/static_check.py <target_skill_dir> --out <workspace>/iteration-0/static.json
```

`<skill-eval-path>` is the absolute path to the installed `skill-eval` skill directory. The orchestrator resolves this via the standard plugin layout (`~/.claude/plugins/cache/<marketplace>/skill-eval/...`) or by glob.

### Fallback when skill-eval is not available

Log a one-line warning ("Phase 2.5 skipped — `skill-eval` not installed; structural axes will not be pre-cleared from the prose audit") and proceed to Phase 3. The audit still works without Phase 2.5; the de-duplication advantage is lost but auditors will still find real prose defects.

## Phase 11 location-aware classifier behavior

For SKILL.md targets, the auto-mode classifier behavior depends on the file's location:

| Location | Classifier behavior |
|---|---|
| `plugins/<name>/skills/<name>/SKILL.md` (marketplace source) | Does NOT trigger — this is a plugin artifact (source), not installed config |
| `~/.claude/skills/*/SKILL.md` (installed) | DOES trigger — this is installed Claude Code config |
| `~/.claude/plugins/cache/<marketplace>/<plugin>/skills/<name>/SKILL.md` (plugin cache) | DOES trigger — same as installed |
| Any other location (e.g., user's personal scratch) | Treat as marketplace source unless the file is referenced from a `~/.claude/` config |

When the classifier triggers, follow the playbook in `references/claude-md-specifics.md` ("Phase 11 auto-mode classifier playbook" section). The mechanism is identical to CLAUDE.md targets; only the trigger location differs.

For same-skill artifact synchronization: if a Phase 9 safety-checker flags that the fix needs synchronized edits to `references/*.md` or `scripts/*.py` in the same skill directory, apply those Edits as part of the same approved fix. The classifier behavior applies per file based on its location, not as a single transaction.

## Phase 11.5(c): Post-fix static re-check

If Phase 2.5 produced a baseline `static.json`, re-execute the same command with the output redirected to `<workspace>/iteration-N/static.json` (where N is the current iteration number). This captures the post-fix static state so Phase 12's ship-ready stop criterion can compare against fresh `score` / `warnings` values.

```bash
python3 <skill-eval-path>/scripts/static_check.py <target_skill_dir> --out <workspace>/iteration-N/static.json
```

If Phase 2.5 was skipped (skill-eval not available), skip Phase 11.5(c) too — the Phase 12 row for skill-eval simply does not fire.

## Marketplace root detection (Phase 7 sibling-skill discovery)

When `target_type == "skill-md"`, Phase 7 redundancy-checker asks "is this rule duplicated by a sibling skill?". To answer, the main thread needs to know which sibling skills are installed.

Resolution strategy (try in order):

1. If `target_file` is inside `plugins/<name>/skills/<name>/SKILL.md` under a path that has `.claude-plugin/marketplace.json` at the root, glob `<marketplace_root>/plugins/*/skills/*/SKILL.md` and read each frontmatter for `name` + `description`.
2. If no marketplace root is found, glob `~/.claude/plugins/cache/*/<*>/skills/*/SKILL.md` for installed plugin skills.
3. If both fail, pass an empty `sibling_skills` list to the redundancy-checker. The checker will only compare against `skill-creator` and `skill-eval` (always-relevant authorities), not sibling skills.

Document the resolution outcome in the iteration log so the user can see whether sibling comparison was active or not.

# skill-md-specifics

Target-type-specific reference for `target_type == "skill-md"`. Loaded by the main thread at Phase 2 after target type is detected. Owns: exclusion defaults, common shared-blind-spot patterns, `skill-eval` integration for Phase 2.5 and Phase 11.5(c), and Phase 11 location-aware classifier guidance.

## Exclusion defaults

Pre-load these as suggested exclusions at Phase 2. The user can deselect any that don't apply.

For the **Claude Code official `subagent_type` values** exclusion (previously item 1 here), see `references/shared-blind-spots.md` — it now lives there as a shared exclusion default because both target types need it. The orchestrator merges it into the pre-loaded list at Phase 2.

1. **Placeholder conventions** — any `<placeholder>` token inside a path template, command shape, formula, or example is a runtime substitution by the executor (e.g., `<workspace>`, `<marketplace_root>`, `<name>`, `<plugin>`, `<marketplace>` in path globs; `<N>`, `<threshold>` in formulas). These are NOT undefined terms — they are template parameters that the calling phase replaces with concrete values.

   **`<workspace>` resolution** — `<workspace>` resolves to `tmp/parallel-audit-workspace/` (relative to the **target marketplace root** being audited — i.e., the project the user is auditing, not this plugin's install location). The orchestrator auto-creates the directory on first write, and the `tmp/` prefix keeps everything under the gitignored scratch area required by the project-root CLAUDE.md `## Temporary Files` rule. Never write workspace artifacts under `plugins/<name>/skills/` or under any other tracked path — published plugins must not carry audit history.
2. **Cross-skill references that the SKILL.md author intentionally leaves as informational pointers** — e.g. "see skill-creator's references/schemas.md" where the load-bearing content is also inlined. Distinguish "broken reference" (REAL defect, no resolution path) from "informational pointer" (intentional courtesy).
3. **Frontmatter content** — `description` length, trigger phrasing, etc. are owned by `skill-eval`'s static axes; do not re-flag here.
4. **(Conditional) Structural defects covered by skill-eval `static_check`** — only added when Phase 2.5 successfully ran and produced a `static.json`. Append this exclusion to the list **before Phase 4 dispatches**, with this literal text:

   > Structural defects already flagged by skill-eval static_check are out of scope for this audit — see `<workspace>/iteration-0/static.json` for the per-axis results. Auditors that want to verify a specific axis Read the file path; do not re-flag axes covered by the static_check.

The user can add skill-specific intentional design at Phase 2 — e.g., "this section is intentionally terse for triggering reasons" or "this skill intentionally duplicates a sibling's rule because the sibling is not always installed".

## Common shared-blind-spot patterns

Phase 6.5 `false-positive-detector` should be aware of these patterns for SKILL.md targets:

- **Auditors flag path-template placeholders such as `<marketplace_root>` / `<workspace>` / `<name>` as undefined** → FALSE (covered by exclusion default 1 — these are runtime substitutions inside path globs, command shapes, or formulas, not undefined terms)
- **Auditors flag a cross-skill schema reference as "unverifiable"** → REAL only if the load-bearing content is not also inlined; FALSE if it's an informational pointer (exclusion default 2)
- **Auditors flag frontmatter description as "too long / too short"** → FALSE (exclusion default 3; skill-eval owns this)
- **Auditors flag the cost-tier table as "missing the deep tier rationale"** → KNOWN ASYMPTOTE; the per-tier when-to-use column already documents the rationale, but auditors keep wanting a separate "why these tiers" paragraph

For the **`subagent_type: general-purpose`** FP pattern (previously listed here), see `references/shared-blind-spots.md` — it now lives there with the matching shared exclusion default.

For target-type-agnostic patterns that apply equally to claude-md and skill-md targets (e.g., the `(N − threshold + 1)` "missing rationale" pattern), see `references/shared-blind-spots.md`. Phase 6.5 should treat that file's entries plus the entries above as one combined known-FP set.

## Phase 2.5: Pre-audit static check

Before the main audit, run `skill-eval`'s `static_check.py` on the target SKILL.md — **only if `skill-eval` is installed as an external dependency**. `skill-eval` is NOT bundled in this marketplace (`almondoo-claude-plugins`); the integration is preserved as an optional capability for users who have installed `skill-eval` from a different source.

### Purpose (three roles, when skill-eval IS available)

1. **Hard-fail gate** — if the static check returns `hard_fail: true` (e.g., missing frontmatter, invalid YAML), abort the audit and surface the static evidence to the user. Multi-agent prose audit on a structurally broken SKILL.md wastes tokens.
2. **De-duplicates work** — the static axes (frontmatter validity, body line count, MUST/NEVER density, emoji, progressive disclosure, reference integrity) cover the structural domain. Pre-running and passing the `static.json` to Phase 4 auditors via the exclusion list hardens the delegation: auditors get the static result as context and explicitly do not re-flag those axes.
3. **Calibrates Phase 2 defaults** — if the static check reports a short body (≤100 lines), suggest reducing `N` (e.g., `N=3` already the default, but tell the user prose-defect surface is small). If body is long (>500 lines), keep defaults but flag potential cost (>500k tokens per iteration even at N=3).

### Command shape

```bash
python3 <skill-eval-path>/scripts/static_check.py <target_skill_dir> --out <workspace>/iteration-0/static.json
```

### Resolving `<skill-eval-path>` (try in order, take first hit)

Stop at the first path that contains `scripts/static_check.py`:

1. **Explicit path**: `skill_eval_path` passed by the user at Phase 2, or the `SKILL_EVAL_PATH` env var if set. This is the persistent override for users who keep skill-eval source outside marketplace cache.
2. **Plugin cache**: glob `~/.claude/plugins/cache/*/skill-eval/skills/skill-eval/scripts/static_check.py`. If the user installed skill-eval via multiple marketplaces, deduplicate by path and take the first hit.
3. **Not found**: log the warning below and skip Phase 2.5.

> **Do not look in `tmp/`**. The `tmp/skill-eval/...` path holds skill-eval's own evaluation workspace artifacts (iteration-N/ output), not source code. Source must come from an installed plugin location or the explicit override path above.

### Fallback when skill-eval is not available

Log a one-line warning ("Phase 2.5 skipped — `skill-eval` not available at any of the resolved paths; structural axes will not be pre-cleared from the prose audit, but the prose audit itself proceeds normally") and proceed to Phase 3. The audit still works without Phase 2.5; the de-duplication advantage is lost but auditors will still find real prose defects.

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

### Resolution strategy (try in order; first successful path wins)

Concrete fallback chain — each step is independent and the orchestrator stops at the first one that produces a non-empty sibling list.

1. **Source-marketplace globbing** — assume `target_file` is inside a marketplace source layout. Walk up parent directories from `target_file` (max 6 levels up) looking for a `.claude-plugin/marketplace.json` file. If found, use that directory as `<marketplace_root>` and glob `<marketplace_root>/plugins/*/skills/*/SKILL.md`. Read each frontmatter's `name` + `description`. Exclude the audit target itself from the list.
2. **Installed-plugin globbing (current marketplace)** — glob `~/.claude/plugins/cache/<current-marketplace>/*/skills/*/SKILL.md`. If `<current-marketplace>` is unknown (e.g., the user invoked the skill outside a marketplace context), substitute `*` and accept any matched installed plugin.
3. **Installed-plugin globbing (all marketplaces)** — fallback to `~/.claude/plugins/cache/*/*/skills/*/SKILL.md`. This may return many results across user-installed marketplaces; deduplicate by `name` and prefer first-seen.
4. **`SKILL_EVAL_SKILLS_DIR` env var** — if the user has set `SKILL_EVAL_SKILLS_DIR=/path/to/installed/skills`, glob that path for `**/SKILL.md`. This is the explicit user override path.
5. **Manual list** — accept a user-provided `sibling_skills` list at Phase 2 (the user pastes `name + description` pairs in free text). Useful when the user knows exactly which siblings matter and wants to bypass discovery.
6. **Empty list fallback** — if all of the above produce nothing, pass an empty `sibling_skills` list to the redundancy-checker. The checker still compares against the upstream authority `skill-creator` (which is broadly assumed available); the per-marketplace sibling comparison is just lost.

### Always-relevant authorities (no discovery needed)

Regardless of discovery outcome, the redundancy-checker always compares against:

- **`skill-creator`** (the canonical SKILL.md authoring authority — patterns, anatomy, writing style). Comparison treats this as an upstream rule source even if not explicitly in `sibling_skills`.
- **`skill-eval`** *only if it was successfully resolved at Phase 2.5* (above). If skill-eval was not resolved, do not compare against it as an authority since the user has not installed it and the assumption that rules are "duplicated by skill-eval" would not be actionable for the reader.

### Logging the outcome

Document the resolution outcome in the iteration log:

- `sibling_discovery: source-marketplace | installed-current | installed-all | env-var | manual | empty-fallback`
- `siblings_found: <count>`
- `siblings_sources: [<marketplace_root> | <env_var_value> | <manual> | <list of cache paths>]`

So the user can see whether sibling comparison was active or not, and which strategy produced the list.

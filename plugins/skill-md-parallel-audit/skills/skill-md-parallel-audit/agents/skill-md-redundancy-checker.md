# skill-md-redundancy-checker

## Role

For each REAL convergent issue that passed Phase 4.5 false-positive filtering, decide whether the rule the issue concerns is **already covered by another skill** in the same marketplace or by the official Anthropic skill-creator's documented patterns. If so, the right fix is to compress or delete the rule and link to the canonical source — not to refine its wording. This phase prevents the workflow from sinking effort into polishing rules that duplicate sibling skills.

This is the SKILL.md analogue of claude-md-parallel-audit's `default-redundancy-checker`. The CLAUDE.md version asks "is this duplicated by Claude Code's default system prompt?". The SKILL.md version asks "is this duplicated by **another skill** the reader is expected to know about?". The asymmetric cost is the same: a wrongly-deleted load-bearing rule degrades the skill; a wrongly-kept redundant rule wastes context and reader attention.

## Why this matters

SKILL.md files commonly inherit conventions from upstream tooling:

- `skill-creator` documents the standard SKILL.md anatomy, frontmatter requirements, progressive disclosure rules, and writing-style guidance ("explain why, not heavy-handed MUSTs"). A SKILL.md that re-explains these in its own body adds zero unique signal.
- `skill-eval` (this marketplace) owns structural quality scoring (frontmatter validity, body length, MUST/NEVER density, reference integrity). A SKILL.md that asserts its own structural correctness rules duplicates skill-eval's check axes.
- Sibling plugins in the same marketplace sometimes share workflow phases (e.g., AskUserQuestion conventions, parallel-dispatch patterns). A SKILL.md that re-derives these from scratch instead of referencing the sibling is redundant.

Without this phase, Phase 5 will default to KEEP for every fix candidate. This wastes user attention on rules that should be deleted, and gradually inflates SKILL.md with content that adds no behavioral signal.

## Input

You will be given:

1. **`target_file`** — absolute path to the SKILL.md being audited
2. **`convergent_issues`** — list of REAL fix candidates from Phase 4.5, each with:
   ```
   issue_id: A
   line: 31
   summary: "L31-34 SKILL.md re-explains progressive disclosure (references/ / scripts/ / assets/) — already in skill-creator's Anatomy section"
   relevant_section_text: <verbatim text of the rule the issue concerns, ±10 lines context>
   ```
3. **`section_purposes`** — the map from Phase 1.5 (section heading → 1-line purpose)
4. **`sibling_skills`** — list of installed sibling skill names + descriptions (when available; the orchestrator collects this from the marketplace or from a manual list). Used to spot cross-skill duplication.

## Task

For each convergent issue:

1. Read the `relevant_section_text` carefully.
2. Identify the **specific rule(s)** the issue concerns (a section can contain multiple rules; focus on the one with the defect).
3. For each rule, ask: **is this rule's content already documented in skill-creator, in skill-eval, or in a sibling skill the reader is expected to know about?**

Use your awareness of common SKILL.md conventions to judge. Examples of upstream-documented content that often duplicates SKILL.md text:

- "Use a YAML frontmatter with `name` and `description`" → in skill-creator's "Anatomy of a Skill" + "Write the SKILL.md" sections
- "Keep SKILL.md under 500 lines" → in skill-creator's "Progressive Disclosure" section
- "Prefer the imperative form in instructions" → in skill-creator's "Writing Patterns" section
- "Explain why instead of heavy-handed MUSTs" → in skill-creator's "Writing Style" section
- "Bundle scripts in scripts/, references in references/" → in skill-creator's "Anatomy of a Skill"
- "Use AskUserQuestion for confirmations" → typically in user's global CLAUDE.md, not skill-specific
- Triggering conventions (e.g., "make descriptions pushy") → in skill-creator's "Write the SKILL.md" section

4. Classify each issue as one of:

- **KEEP** — the rule has unique non-default value. The defect is real and the fix should refine the wording.
- **SIMPLIFY** — part of the rule duplicates upstream content, but part has unique value. Suggest a compressed wording that retains only the unique portion and links to the canonical source.
- **REMOVE** — the rule is fully covered by upstream content. The fix should be deletion + optional 1-line pointer to where the reader can find it.

5. **Hedge when uncertain.** If you cannot tell whether upstream content covers the rule (e.g., the upstream guidance is loosely worded, or you're not sure if the SKILL.md author intended a specific deviation), classify as **KEEP** and note your uncertainty. Better to keep a marginal rule than to delete a load-bearing one based on a guess. Use "I am inferring, not citing" framing per the user's Forthright Assessment rule.

## Output format

Return a markdown table:

| issue_id | classification | unique_value_summary | suggested_action_if_simplify_or_remove |
|---|---|---|---|
| A | REMOVE | None — skill-creator's "Progressive Disclosure" section already specifies references/ / scripts/ / assets/ structure | Delete L31-34. Add a 1-line pointer: "see skill-creator's `Anatomy of a Skill` section for the full structure." |
| B | SIMPLIFY | The frontmatter validity rule duplicates skill-eval's `frontmatter.*` static axes, but the description-length 50–1536 char range is a specific calibration this skill maintains. | Compress to: "Description length: 50–1536 chars (the rest of frontmatter validity is enforced by `skill-eval`'s static_check)." |
| C | KEEP | The 7-axis classification for HIGH-severity defects is unique to this skill's audit semantics; no upstream skill specifies this taxonomy. | Refine wording per the original defect (Phase 5 should refine, not delete). |
| D | KEEP (uncertain) | I am inferring that skill-creator's writing-style guidance does not specifically cover "exclude code spans when counting MUST density" — but I have not verified against the most recent skill-creator skill. | Refine wording, but consider explicit verification by the user if removal is appealing. |

## Constraints

- **Do not draft the actual fix.** Phase 5 owns drafting. Your `suggested_action_if_simplify_or_remove` is a hint for Phase 5, not a finalized fix.
- **Lean toward KEEP when uncertain.** A wrongly-removed load-bearing rule degrades all future invocations of the skill; a wrongly-kept redundant rule wastes a small amount of context. Asymmetric cost.
- **Cite the specific upstream content** you believe duplicates the rule. Vague "I think skill-creator says this" is not useful. Quote or paraphrase the specific section name and the upstream rule.
- **Mark unverified claims explicitly.** Per the user's "Forthright Assessment" section in `~/.claude/CLAUDE.md`: use "I am inferring" / "I have not verified" when you cannot point to a documented upstream rule.
- **Do not re-audit the file.** Only assess the issues passed in.
- **Do not assess `section_purposes` correctness.** Take them as given — they represent the user's confirmed intent. Use them only to disambiguate which rules in a section are load-bearing.
- **Sibling skills are referential, not authoritative.** If a sibling skill happens to have the same rule but neither claims canonicality, prefer KEEP (the duplication is across peers, not subordination to a documented authority). Reserve SIMPLIFY/REMOVE for cases where the upstream content is the **canonical source** (skill-creator's official sections, or a clearly-designated owner skill in the marketplace).

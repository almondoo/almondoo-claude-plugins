# Evaluation Axes — details

The rationale behind each score skill-eval emits, and why each axis is chosen. A deeper companion to the table in `SKILL.md`.

---

## Static layer

### Why measure static at all

Even when the dynamic benchmark shows "with > without", that may just be the LLM working harder on the day. A skill with poor structure:

- Fails to reproduce in the recipient's environment (implicit tool dependencies).
- Becomes hard to fix when a future Claude model changes behavior.
- Leaves readers unsure of "when should I invoke this".

These are invisible to runtime benchmarks and must be caught statically.

---

### frontmatter

| axis | intent | typical failure cause |
|---|---|---|
| `frontmatter.present` | A YAML frontmatter must exist — the Claude Code skill loader skips files that lack it | missing `---` / malformed block |
| `frontmatter.name_matches_dir` | If `name:` does not match the directory name, the plugin's skill-discovery logic breaks | author renamed the dir but forgot to update `name:` |
| `frontmatter.description_present` | description is the sole signal for triggering — an empty one means the skill is never invoked | left out when copying from a template |
| `frontmatter.description_has_trigger` | A description that only states "what it does" without "when to use" under-triggers (the official skill-creator flags this too) | abstract phrasing like "Format data" |
| `frontmatter.description_length` | Anthropic caps `description + when_to_use` at **1,536 chars** combined (skills.md § "Skill descriptions are cut short"). The 50-char lower bound is a community heuristic — overly short descriptions tend to under-trigger | too verbose / too terse |

#### What makes a description good

From the official skill-creator examples:

- Bad: `"How to build a dashboard"` — says *what* but not *when*.
- Good: `"How to build a simple fast dashboard to display internal Anthropic data. Make sure to use this skill whenever the user mentions dashboards, data visualization, internal metrics, or wants to display any kind of company data, even if they don't explicitly ask for a 'dashboard.'"` — when, what, and edge-cases are all present.

skill-eval uses a trigger-vocabulary heuristic (`when` / `use` / `whenever` / `if` / `before` / `after` / `trigger`) as a proxy — do not over-trust it. The human reads `report.md` and decides.

---

### body

| axis | intent |
|---|---|
| `body.line_count` | The official guideline target is ≤ 500 lines. A long body eats context every turn and raises the chance Claude skims past important parts |
| `body.must_never_density` | A high density of `MUST` / `NEVER` / `ALWAYS` signals that the author did not explain *why*. Occurrences inside code spans (backticks / fenced blocks) are treated as meta-mentions and excluded |
| `body.no_emoji` | Anthropic's global rule is "Only use emojis if the user explicitly requests it". Emoji in the skill body easily bleeds into outputs and overrides user preference. Code-span occurrences are exempt (so checkbox glyphs etc. used for illustration are fine) |

#### Why density matters

From the official skill-creator "Writing Style" section:

> Try to explain to the model why things are important in lieu of heavy-handed musty MUSTs. Use theory of mind and try to make the skill general and not super-narrow to specific examples.

Overusing `MUST`:

- The LLM treats the wording as a literal rule and loses flexibility at edge cases.
- It's a tell that the author did not think about *why*. Another Claude model reading it later may interpret behavior differently.
- Each rule needs its own line, inflating skill size.

More than 10 per 100 lines is too many. This is a rule of thumb.

---

### structure

| axis | intent |
|---|---|
| `structure.has_progressive_disclosure` | Long skills should be split into `references/` / `scripts/` / `assets/`. Short skills (~100 lines) do not need this |
| `structure.scripts_referenced_from_body` | A script under `scripts/` that is never named in the body is dead code. The check looks for the filename (e.g. `scripts/foo.py`) being mentioned in `SKILL.md` |
| `structure.references_referenced_from_body` | Same idea for `references/` |

Scripts and references that the body never names are not loaded by Claude (load-on-demand), so they are 100% inert.

---

## Manual perspective (not yet mechanized — reviewer checklist)

Observations raised by the iteration-2 baseline (without-skill evaluation) that are hard to mechanize. These are not part of `static_check.py`, but are useful inputs for a human reviewer or an LLM grader prompt.

| axis | how to check | why not mechanized yet |
|---|---|---|
| `tool_usage_explicit` | For each procedural step in SKILL.md, is the tool to use (Read / Edit / Bash / etc.) named explicitly | "step boundary" has no deterministic parse — authors mix headings, numbered lists, and prose |
| `cross_file_consistency` | Do `SKILL.md` / `plugin.json` / `README.md` / `marketplace.json` agree on category count, defaults, and skill names | which fields "must agree" varies per plugin, so it generalizes poorly |
| `destructive_ops_safety_alignment` | Are destructive ops defaulted to deny / ask, aligned with the global CLAUDE.md Tier-3 rule | classifying "what is destructive" requires LLM judgment |
| `output_format_specified` | Are the output file format (JSON schema, file name, newline policy) explicitly stated | the threshold for "explicit" is fuzzy |

These are kept here as the prompt material to feed a future LLM-grader run.

---

## Dynamic layer

### Why A/B

The only way to know "is this skill helping" is to run the same prompts with and without it. Same idea as the skill-creator benchmark.

### Metrics observed

| metric | what it means | how to read it |
|---|---|---|
| `pass_rate` delta | with − without. The marginal value of the skill itself | ≥ +0.2 means "clearly valuable" |
| `time_seconds` delta | with tends to be slower (the body has to be read) | up to +30 s is tolerable; beyond that, consider compressing the body |
| `tokens` delta | with consumes more | judge against the pass_rate gain |
| stddev | variance — relevant once runs_per_configuration ≥ 3 | flaky if stddev > mean × 0.3 |
| `differentiating_assertions` | assertions that only the with-skill side passed | zero of these means the skill isn't really doing anything |

### Notes

- **with-skill being slower is normal** — reading the body adds startup latency. The question is whether the slowdown is justified by the pass_rate gain.
- **without_skill passing perfectly** — the task is solvable by Claude alone, so the prompt is the wrong evaluation subject; rethink the prompt selection rather than the skill.
- **with_skill is worse than without_skill** — the skill is likely enforcing the wrong procedure (e.g. a `MUST` is pushing an incorrect approach).

---

## Verdict heuristics

The rationale behind the decision logic mentioned in `SKILL.md`:

| verdict | condition | intuition |
|---|---|---|
| **Ship-ready** | static ≥ 0.8 AND pass_rate delta ≥ +0.2 | structurally sound and empirically helpful |
| **Needs work** | not the above, but not net-negative | one more round of polish before shipping |
| **Net negative** | pass_rate delta ≤ 0, or time ≥ 2× AND tokens ≥ 2× | better off without the skill |
| **Inconclusive** | runs_per_configuration < 3, or stddev > mean × 0.3 | not enough samples / too noisy |

These are not absolutes. E.g. a `time delta +200s` can still be worth shipping if the pass_rate climbs by +0.6. The user makes the final call.

---

## References

- "Skill Writing Guide" and "Description Optimization" sections of claude-plugins-official `skill-creator/SKILL.md`
- claude-plugins-official `skill-creator/references/schemas.md` (benchmark.json schema)

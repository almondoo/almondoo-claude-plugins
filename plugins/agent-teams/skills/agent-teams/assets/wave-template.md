# Wave composition template

A Wave is a group of tasks that can be worked on in parallel. Running 1-2 waves per session (~6 tasks total) is the realistic size.

## Typical pattern: "4 in parallel + 2 blocked_by" (6 tasks)

The naming below uses the `W<n>-<scope-prefix><id>` task convention (defined further below) and the `impl-<area><N>` Implementer handle convention. Wave 1 (`W1-*`) corresponds to the four parallel tasks; Wave 2 (`W2-*`) corresponds to the two `blocked_by`-gated tasks.

```
Wave 1 (4 tasks in parallel):
  - W1-D1: doc-area task (owner: impl-doc1)
  - W1-D2: doc-area task (owner: impl-doc2)
  - W1-A1: api-area task (owner: impl-api1)
  - W1-A2: api-area task (owner: impl-api2; possibly security-critical)

Wave 2 (2 tasks in parallel, every Wave 2 task blocked_by every Wave 1 task):
  - W2-AI1: ai-area task (owner: impl-ai1 — or impl-api1 re-assigned once Wave 1 finishes)
  - W2-UI1: ui-area task (owner: impl-ui1 — or impl-api2 re-assigned once Wave 1 finishes)
```

With 4 Implementers, this lets you process 6 tasks in two stages. Wave 1 finishes quickly in parallel; during Wave 2, two Implementers pick up the next tasks while the other two wait idle (or can shut down early).

## Naming convention: `W<wave>-<scope-prefix><id>`

| Prefix | Area | Example |
|---|---|---|
| `D` | doc / shared / pure helper / schema | `W1-D1`, `W1-D2` |
| `A` | API route / service / security / observability | `W1-A1`, `W1-A2` |
| `AI` | AI / ML / safety / inference | `W2-AI1` |
| `UI` | components / pages / client-side helpers | `W2-UI1` |

Example: `W1-A1` = the first API-area task in Wave 1. Prefixing task subjects with `[W1-A1] <summary>` makes the TaskList easier to read.

## Team composition patterns (by scale)

### Small wave (1-2 tasks) — 2 teammates

```
Lead + Implementer×1 + Reviewer×1 (Reviewer also covers Tester; Lead may verify directly at end of wave)
```

### Medium wave (3-5 tasks) — 3-4 teammates

```
Lead + Implementer×1-2 + Reviewer×1 (security combined) + Tester×1
```

### Large wave (6+ tasks) or security-critical — 5-6 teammates

```
Lead + Implementer×2-3 + Reviewer×1 + Security Checker×1 (dedicated) + Tester×1
```

## Owner-separation strategy (race-condition prevention)

The rule is **1 file = 1 owner**. Split tasks along file boundaries.

Example (substitute your own module names):
- `lib/<area>/document/` → impl-doc1 / impl-doc2
- `lib/<area>/api/` / `lib/<area>/security/` / `lib/<area>/observability/` → impl-api1 / impl-api2
- `lib/<area>/ai/` → impl-ai1 (or combined)
- `lib/<area>/notifications/` / `components/<area>/` → impl-ui1 (or combined)

Each task description must state "Owned files (exclusive)" and "Forbidden (owned by other teammates)" clearly.

## Wave execution flow

For Phase 1 → Phase 4 operating procedure, see the **Workflow** section of `SKILL.md` (it is the single source of truth — duplicating the procedure here previously caused drift). This template focuses on wave **composition** (sizing / naming / owner separation); execution sequencing lives in SKILL.md.

## Wave completion conditions (checklist)

- [ ] All tasks `completed` (confirmed in TaskList)
- [ ] Every commit has per-path staging with no off-target contamination (`git log --stat`)
- [ ] All Reviewer PASS, with zero Critical/Important
- [ ] Tester's final regression PASS (counts + typecheck + lint all green)
- [ ] Working tree clean, push not performed (`git status`)
- [ ] commit messages follow the convention (`feat\|fix(scope): #<issue> ...`)

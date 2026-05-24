# Wave composition template

A Wave is a group of tasks that can be worked on in parallel. Running 1-2 waves per session (~6 tasks total) is the realistic size.

## Typical pattern: "4 in parallel + 2 blocked_by" (6 tasks)

```
Wave A (4 tasks in parallel):
  - task #1: domain-D1 (assigned: Implementer A)
  - task #2: domain-D2 (assigned: Implementer B)
  - task #3: domain-A1 (assigned: Implementer C)
  - task #4: domain-A2 (assigned: Implementer D; possibly security-critical)

Wave B (2 tasks in parallel, blocked_by all of Wave A):
  - task #5: domain-AI1 (assigned: Implementer C, picks up after A is done)
  - task #6: domain-UI1 (assigned: Implementer D, picks up after A is done)
```

With 4 Implementers, this lets you process 6 tasks in two stages. Wave A finishes quickly in parallel, and during Wave B two Implementers move on to the next tasks while the other two wait idle (or can shut down early).

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

### Phase 1: Planning
1. Receive the user's request and grasp the overall scope
2. Read the issue / spec and pick 6 items from the backlog (prefer: new helpers / independent / no Prisma migration / no new deps)
3. Decide Wave structure (4 in parallel + 2 blocked_by) and the naming convention (`W<n>-<scope><id>`)
4. Present the plan to the user and get approval

### Phase 2: Spawn (one batch)
1. `TeamCreate` to make the team
2. `TaskCreate` for 6 tasks; set `addBlockedBy` on tasks #5/#6 to encode the Wave structure
3. Copy templates from `assets/spawn-prompts/` and substitute placeholders
4. Spawn Implementer×4 + Reviewer×1 + Tester×1 (+ Security Checker×1 if needed) **in a single message**, in parallel
   - Reviewer/Tester have "wait for SendMessage" baked into their templates

### Phase 3: Execution
- Implementer requests a commit from the Lead → Lead runs the commit → request review → fix Critical/Important → wave completion
- Details: see "Per-task cycle" in SKILL.md Phase 3
- The Tester is only called once at the end of the wave

### Phase 4: Disband
1. After all Reviewer PASS, request a final regression from the Tester
2. On Tester PASS, send shutdown_request to all teammates
3. Once everyone shutdown_approved → `TeamDelete`
4. Report a wave summary to the user

## Wave completion conditions (checklist)

- [ ] All tasks `completed` (confirmed in TaskList)
- [ ] Every commit has per-path staging with no off-target contamination (`git log --stat`)
- [ ] All Reviewer PASS, with zero Critical/Important
- [ ] Tester's final regression PASS (counts + typecheck + lint all green)
- [ ] Working tree clean, push not performed (`git status`)
- [ ] commit messages follow the convention (`feat\|fix(scope): #<issue> ...`)

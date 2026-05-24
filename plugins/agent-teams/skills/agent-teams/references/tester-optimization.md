# Tester request consolidation + Lead direct-verification — detailed reference

The Tester is the teammate that consumes context most heavily during a wave. Repeated per-commit requests have caused unresponsiveness incidents multiple times, so we define consolidation principles and a fallback route.

## 1. Tester request consolidation principle

**Consolidate Tester requests into a single full regression at the end of the wave**. Per-commit vitest verification requests are forbidden.

### Why

- Implementers always report a green `bun vitest run <target>` when they request a commit (self-verification)
- The Reviewer has already approved from a code perspective → these two layers establish per-commit quality
- Asking the Tester to verify every commit means 6+1=7 heavy Bash invocations per wave (6 commits), and the cumulative context pressure causes **unresponsiveness in the latter half of the wave**
  - Real incident: in a past pair of waves, the Tester returned only idle notifications at the final-regression stage and stopped responding with content
  - In subsequent waves, with per-commit requests removed, the unresponsiveness pattern did not recur

### Flow after consolidation

```
Per commit:
  Implementer self-verification → Lead commit → Reviewer review (do NOT call Tester)

End of wave (all commits + all fix commits done + all Reviewer PASS):
  Lead → SendMessage to Tester: "Please run the final full regression" (once only)
    - bun run test:unit (full)
    - bun --filter '*' typecheck && bun run typecheck
    - bun --filter '*' lint && bun run lint
    - git log --stat to confirm each commit's per-path staging
  Tester returns PASS / FAIL in 3 lines (no details needed on PASS)
```

## 2. Lightweight Tester output format

State the following explicitly in the Tester spawn prompt:

### On PASS (3-5 lines is enough)

```
- XXXX/XXXX tests pass (delta +N)
- typecheck OK
- lint OK (only N pre-existing warnings, 0 warnings in new files)
- No off-target contamination
- Push not performed (ahead N commits)
```

### On FAIL, include details

- Blocker test name (e.g. `lib/<your-module>/foo/__tests__/bar.unit.test.ts > "X should reject Y"`)
- Full error message
- For typecheck errors: file:line + error code
- For lint errors: file:line + rule name

### Not needed

- Tables (per-commit detail rows)
- Line-number-annotated analysis (that's the Reviewer's territory)
- Per-metric verdicts (e.g. "12 acceptance-criteria cases covered" is Reviewer's territory)

Excessive detail accelerates context pressure and raises the risk of late-wave unresponsiveness.

## 3. Lead direct-verification fallback route

When the Tester becomes unresponsive (returns only idle notifications, no content responses), the Lead may run verification commands directly via Bash.

### Why this does not bypass the quality gate

- `bun run test:unit` / `typecheck` / `lint` are **read-only objective verification** (zero code changes)
- The result is settled by numeric output, leaving no room for the Lead's subjective judgment
- Per-commit quality is already established by Implementer self-verification + Reviewer PASS; the Tester's final regression mainly confirms "post-accumulation consistency"

### Execution steps

1. Ping the Tester after the expected time elapses (~5 minutes) → only idle notifications, no content → re-request → same
2. The Lead runs directly via Bash:
   ```bash
   bun run test:unit 2>&1 | tail -5
   bun --filter '*' typecheck && bun run typecheck
   bun --filter '*' lint && bun run lint
   git log --stat main..HEAD | head -50
   git status
   ```
3. If numbers satisfy requirements (counts / 0 errors / no off-target contamination), judge PASS
4. When sending shutdown_request, state explicitly "Tester response missing, so the Lead verified on its behalf"

### Tester-unresponsiveness preventive measures

- Enforce the "Tester request consolidation" above (do not send per-commit requests)
- Specify lightweight output format in the spawn prompt
- Expected Tester time = `max(60s, tests count / 100 + 30s)`; flag as anomalous if exceeded 3×

## 4. Expected-time table

| Verification type | Expected time | Anomaly detection (3×) |
|-------------------|---------------|------------------------|
| Single vitest file (~30-50 tests) | 1-5 sec | 15 sec |
| One wave's vitest (~6 files / ~200 tests) | 5-15 sec | 45 sec |
| `bun run test:unit` full (~3000-3500 tests) | 20-30 sec | 1.5 min |
| typecheck (workspace + root) | 10-30 sec | 1.5 min |
| lint (workspace + root) | 5-15 sec | 45 sec |
| All four combined | ~1-2 min | 6 min |

If you exceed 3×, treat as anomalous: send a status-check ping + re-request. If still no response, switch to the Lead direct-verification route.

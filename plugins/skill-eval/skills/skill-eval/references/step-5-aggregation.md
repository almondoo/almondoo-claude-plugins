# Step 5 details — Aggregation

Full per-key `benchmark.json` schema, sample markdown layout, and the stats / missing-data conventions.

---

## Command

```bash
python3 <this-skill-path>/scripts/aggregate_benchmark.py \
  <workspace>/iteration-N \
  --skill-name <target-skill-name> \
  --out <workspace>/iteration-N/benchmark.json
```

The script emits `benchmark.json` plus a sibling `benchmark.md`. The JSON shape mirrors skill-creator's reference (also documented in `skill-creator/references/schemas.md` for users who have it installed) so the same viewer can consume both.

---

## benchmark.json top-level schema

The viewer reads these keys exactly; do not rename them.

- `metadata` — `{ skill_name, iteration_dir, evals_run[], runs_per_configuration }`
- `runs[]` — per-run records:
  ```json
  {
    "eval_id": 1,
    "eval_name": "extract-table-from-pdf",
    "configuration": "with_skill",
    "run_number": 1,
    "result": {
      "pass_rate": 0.667,
      "passed": 2,
      "failed": 1,
      "total": 3,
      "time_seconds": 42.0,
      "tokens": 3800,
      "tool_calls": 0,
      "errors": 0
    },
    "expectations": [...]
  }
  ```
  `tool_calls` / `errors` are currently emitted as `0` placeholders, reserved for future instrumentation.
- `run_summary` — `{ with_skill, without_skill, delta }` each holding `pass_rate` / `time_seconds` / `tokens` stats blocks:
  ```json
  {
    "mean": 0.667,
    "stddev": 0.135,
    "min": 0.5,
    "max": 0.833,
    "n": 3,
    "missing": 0
  }
  ```
  When `n < 2`, `stddev` is `null` (not `0`) — "single sample" and "all-samples-equal" are different signals and must not collide.
- `differentiating_assertions[]` — assertions where `(with_pass_rate − without_pass_rate) ≥ 0.5`, grouped by `(eval_id, text)` so cross-eval pollution does not blur the rates.
- `notes[]` — free-form annotations (e.g. "without_skill could not produce any output for eval-2").

---

## benchmark.md layout

`aggregate_benchmark.py` emits this verbatim:

```
## Summary

| metric    | with_skill | without_skill | delta  |
|-----------|------------|---------------|--------|
| pass_rate | 1.0        | 0.333         | +0.667 |
| time (s)  | 42.0       | 30.0          | +12.0  |
| tokens    | 3800       | 2100          | +1700  |

## Per-eval

| eval                  | config        | pass | time  | tokens |
|-----------------------|---------------|------|-------|--------|
| extract-table-from-pdf | with_skill    | 3/3  | 42.0s | 3800   |
| extract-table-from-pdf | without_skill | 1/3  | 30.0s | 2100   |
```

---

## Missing-data semantics

`stats()` distinguishes "missing measurement" from "measured zero". When a run lacks `timing.json`, its `time_seconds` and `tokens` are `null`; they are excluded from `mean` / `stddev` / `min` / `max` and counted in `missing`. A run with `timing.json: { duration_ms: 0 }` is `0`, included in the mean. This is load-bearing: a half-instrumented benchmark must not silently report `0` as a real datapoint.

The `_cell()` helper in the markdown renderer prints `"n/a (N missing)"` when the mean is `null`, so missing data is visible in the report.

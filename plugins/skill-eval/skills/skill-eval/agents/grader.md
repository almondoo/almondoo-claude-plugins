# Grader prompt

You are grading a single A/B run produced by skill-eval.

## Inputs you will be given

- A **run directory** containing `outputs/` (the files / artifacts the executor produced) and optionally `outputs/SUMMARY.md`.
- A list of **assertions** — short statements that must be objectively checkable against the outputs.

## What to do

1. **Read the outputs first.** Open every file in `outputs/`. Do not skim — assertion grading is the whole point.
2. For each assertion, decide `passed: true | false` with evidence.
   - Evidence MUST quote / point at concrete artifacts (file name, line number, value seen). "Looks fine" is not evidence.
   - If the assertion is programmatically checkable (file exists, regex matches, CSV has column X), **write and run a small script** rather than eyeballing. Scripts are faster and reproducible.
3. Mark `passed: false` when in doubt. False positives here will mislead the benchmark.
4. Do not invent assertions. Score only what was given.

## Output format

Write `grading.json` to the run directory with this exact schema (matches skill-creator's viewer):

```json
{
  "expectations": [
    {
      "text": "Output CSV has a 'Revenue' column",
      "passed": true,
      "evidence": "Found 'Revenue' as first header in outputs/sales.csv line 1"
    },
    {
      "text": "Amount values are numeric, not strings with commas",
      "passed": false,
      "evidence": "outputs/sales.csv row 3 contains '1,234.56' as quoted string"
    }
  ],
  "summary": {
    "passed": 1,
    "failed": 1,
    "total": 2,
    "pass_rate": 0.5
  }
}
```

Field names are load-bearing — the aggregation script and the skill-creator viewer key on exactly `text` / `passed` / `evidence`. Do not rename.

## Watch-outs

- The executor sometimes writes "✅ done" in SUMMARY.md even when outputs are wrong. Trust files, not self-reports.
- An assertion that says "the output mentions X" passes if any artifact mentions X. An assertion that says "X is the value of column Y" requires structural match.
- If `outputs/` is empty, all assertions fail with evidence `"executor produced no outputs"`.

## When you can't grade

If an assertion is too vague to grade objectively (e.g. "the output is good"), still emit it with `passed: false` and evidence `"assertion not objectively verifiable — flag for rewrite"`. The aggregator will surface this.

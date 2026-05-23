# Step 4 details — Grading

Full grader input shape, assertion-kind handling, and script-vs-eyeball guidance.

---

## Grader subagent shape

Once every run has completed, spawn one grader subagent per run. The grader reads `<this-skill-path>/agents/grader.md` (a frontmatter-less prompt template — not a Claude Code agent file, so it cannot be dispatched as one) and applies it to that run's outputs against the assertions from `evals.json`.

```
Read this prompt template: <this-skill-path>/agents/grader.md (absolute path)
Apply it to grade this run:
  Run directory: <workspace>/iteration-N/runs/eval-<id>/with_skill/
  Assertions: <full list from evals.json>
Write grading.json to the run directory.
```

---

## grading.json schema (compatible with skill-creator viewer)

```json
{
  "expectations": [
    {"text": "...", "passed": true,  "evidence": "..."},
    {"text": "...", "passed": false, "evidence": "..."}
  ],
  "summary": {"passed": 1, "failed": 1, "total": 2, "pass_rate": 0.5}
}
```

The field names — `expectations` / `text` / `passed` / `evidence` / `summary` — are read by key in `aggregate_benchmark.py` and by the viewer; **do not rename them**. Note that the **input** schema (`evals.json`) uses `assertions: [{text, kind}]` while the **output** schema (`grading.json`) uses `expectations: [{text, passed, evidence}]`. This asymmetry is intentional: the kind field guides grading style, the output drops it because each row stands on its own once judged.

---

## Programmatic verification

For programmatically verifiable assertions (file existence, regex match, JSON-key presence, etc.), instruct the grader to **write a small script and run it** rather than eyeballing. Eyeballing is slow, unreliable, and inflates with-skill pass rates when the grader is lenient with formatted output. A 6-line `grep`/`jq` invocation produces a deterministic answer.

For assertions that genuinely need human judgment (writing style, tone match, design quality), eyeballing is the only option — the grader records its reasoning in `evidence`.

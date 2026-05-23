# Step 3 details — A/B parallel dispatch

Full subagent prompt templates, safety check, and notification handling. Read when implementing the dynamic layer; the body of `SKILL.md` keeps only the contract.

---

## Cross-eval time-of-day comparability

Dispatch every prompt × both configurations in the **same turn**. Running the baseline later misaligns conditions (time-of-day load on Anthropic infrastructure, model version cache state, network jitter) and ruins the comparability that the entire dynamic layer rests on. If you find yourself splitting dispatch across turns, you instead have two separate small evaluations whose deltas cannot be safely subtracted.

---

## Subagent dispatch shapes

For each prompt, launch two Agents (`subagent_type: general-purpose`) with `run_in_background: true`.

### with-skill subagent

```
Execute this task. You have access to the following skill - read its SKILL.md first
and follow it for the task:

Skill SKILL.md path: <target_skill_path>/SKILL.md

Task: <eval prompt>

Save all outputs (files, final answer) under:
<workspace>/iteration-N/runs/eval-<id>/with_skill/outputs/

When done, write a short summary to outputs/SUMMARY.md describing what you produced.
```

### without-skill subagent

```
Execute this task WITHOUT using any special skill or external reference. Use only
your default tools.

Task: <eval prompt>

Save all outputs under:
<workspace>/iteration-N/runs/eval-<id>/without_skill/outputs/

When done, write a short summary to outputs/SUMMARY.md describing what you produced.
```

---

## Notification handling

The Agent tool's completion notification includes `total_tokens` and `duration_ms`. Persist those **immediately** to `<run-dir>/timing.json` — once the completion notification has passed, the values cannot be retrieved later. Write per child agent as soon as its notification arrives, not in a batch at the end.

```json
{ "total_tokens": 84852, "duration_ms": 23332, "total_duration_seconds": 23.3 }
```

Runs with no `timing.json` are treated as `null` by the aggregator and excluded from stats (so they don't masquerade as a zero — this is the entire reason for the missing-vs-zero distinction in `aggregate_benchmark.stats`).

---

## Dispatch decision criteria

- **Safety check**: skim the target SKILL.md before dispatch. Skills that perform external writes (PR creation, email send, Slack post, etc.) need sandboxing rather than plain subagents. If unsafe, warn the user and offer to skip the dynamic layer (Step 5 onwards reads `benchmark.json` if present, so a static-only run is well-defined).
- **Subagent soft cap = 6 per iteration**: `2 × prompts × runs_per_configuration > 6` is the threshold to reduce. With 3 prompts × 1 run = 6 subagents you are already at the cap; bumping `runs_per_configuration` to 3 would land at 18 and break the same-turn guarantee. Reduce at Step 2 confirmation (drop a prompt or keep `runs_per_configuration` at 1) rather than batching across turns.

Why this cap exists: dispatching more than ~6 in a single turn risks main-thread context bloat (each completion notification consumes tokens) and increases the chance one or two stall while the rest finish, eroding the comparability you bought by same-turn dispatch.

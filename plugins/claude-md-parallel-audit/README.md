# claude-md-parallel-audit

Multi-agent parallel audit of CLAUDE.md (or any similar agent-instruction file
such as `CLAUDE.local.md`, `AGENTS.md`, `GEMINI.md`) for **HIGH-severity**
quality issues: missing qualifiers, grammar errors, terminology drift,
cross-section logical contradictions, implicit premises, incomplete
enumerations, undefined terms.

## How it works

1. Dispatch **N independent subagents** (default `N=9`) to audit the same file.
2. Aggregate findings by **reproducibility** — only issues flagged by **≥ K of N**
   instances (default `K=4`) are treated as real signal. Findings from a single
   instance are discarded as noise.
3. Triage results into:
   - **New fixable defects** — propose targeted fixes via `AskUserQuestion`.
   - **Known architectural tensions** the user has already accepted — list separately.
4. Iterate until convergence (no new HIGH-severity issues reproduced ≥ K times),
   capped at `max_iter` rounds.

## Install

```
/plugin marketplace add almondoo/almondoo-claude-plugins
/plugin install claude-md-parallel-audit@almondoo-claude-plugins
```

## Usage

```
/claude-md-parallel-audit:claude-md-parallel-audit
```

The skill auto-activates when the user asks to **audit / review / verify /
check the quality** of a CLAUDE.md or similar instruction file, or mentions
*multi-agent audit*, *convergence audit*, *parallel review*, *instruction file
consistency*, or wants high-confidence reproducibility on defects in a long
instruction file.

## Layout

```
claude-md-parallel-audit/
├── .claude-plugin/
│   └── plugin.json
├── skills/
│   └── claude-md-parallel-audit/
│       ├── SKILL.md                       # main skill definition
│       ├── agents/                        # specialist subagents
│       │   ├── auditor.md
│       │   ├── default-redundancy-checker.md
│       │   ├── false-positive-detector.md
│       │   └── fix-safety-checker.md
│       └── evals/
│           └── evals.json                 # trigger / behavior tests
└── README.md
```

## Distinction from template-comparison audits

This skill specifically uses **parallel independent audits + reproducibility
threshold**, not template matching. It is complementary to (not a replacement
for) template-comparison audits such as
`claude-md-management:claude-md-improver` from the official marketplace.

## License

[Apache-2.0](../../LICENSE)

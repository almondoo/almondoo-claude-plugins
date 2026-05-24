# reviewing-dependency-updates

A Claude Code skill that decides whether a dependency update PR — from Dependabot, Renovate, or a manual bump — is safe to merge, using a **security-first three-phase checklist**, and proposes a recommended action (`merge` / `hold` / `do-not-merge`). It never merges on green CI alone.

## Why this exists

The most common failure mode when reviewing dependency-update PRs is to assume "CI passes, therefore it's safe." The PR Dependabot / Renovate authors **is** trustworthy, but **the package being bumped to is third-party code**, and green CI only certifies that this project's tests still pass — not that the code is safe.

This skill verifies each PR phase by phase:

| Phase | Focus | Main checks |
|-------|-------|-------------|
| **Phase 1: Basic verification** | CI and version jump | Every matrix cell is SUCCESS / `mergeable=MERGEABLE` / patch vs. minor vs. major |
| **Phase 2: Security verification** | Supply-chain trust | GitHub Security Advisory / official org / recent maintainer changes / transitive-dependency diff size / SHA pinning for GitHub Actions |
| **Phase 3: Change-impact analysis** | Compatibility | Breaking changes in the changelog / language-version requirements (`go` directive, `engines`, etc.) against the CI matrix minimum / lockfile consistency |

If any phase surfaces a blocker, the PR is classified as **do-not-merge** immediately and the checklist stops there.

## Output

Final verdicts are reported to the user in this table form:

```
| PR | Version change | CI | Security | Breaking | Verdict | Recommended action |
|----|---------------|----|----------|----------|---------|--------------------|
```

The skill only **recommends** an action (`merge` / `close` / `hold`) — **it never merges automatically**. Only PRs the user has explicitly approved are then processed serially.

## Install

```
/plugin marketplace add almondoo/almondoo-claude-plugins
/plugin install reviewing-dependency-updates@almondoo-claude-plugins
```

## Usage

No explicit trigger is required. The skill activates automatically for prompts like:

- "Review the Dependabot PRs."
- "Should I merge this Renovate update?"
- "We have a backlog of dependency bump PRs — go through them."
- Whenever `gh pr list` surfaces a dependency update PR and the user asks for a verdict.

## Why phase the checks

Blockers are cheapest to detect in the earliest phase.

- Phase 1 takes one `gh pr view` call.
- Phase 2 requires package research, but is skippable for PRs that already failed Phase 1.
- Phase 3 requires reading the changelog and is the most expensive, so it is skippable for PRs that failed Phase 1 or 2.

Reading a changelog for a PR whose CI is red is wasted work, so phases always run in order.

## License

Apache-2.0

---
name: reviewing-dependency-updates
description: Use when reviewing dependency update PRs from Dependabot, Renovate, or manual bumps — before approving or merging any dependency-bump PR. Walks the user through a security-first three-phase checklist (basic CI / mergeability, supply-chain trust, breaking-change and runtime-compatibility impact) instead of merging on green CI alone. Trigger when the user says "review dependabot PRs", "check this renovate PR", "should I merge this bump", or whenever `gh pr list` surfaces a dependency update PR. Classifies each PR as merge / hold / block and proposes a recommended action — never auto-executes the merge.
---

# Reviewing Dependency Updates

## Overview

A skill for deciding whether a dependency update PR is safe to merge, using a **security-first**, phased checklist. **Never decide on CI status alone.**

**Core principle:** The PR Dependabot / Renovate authors is itself trustworthy, but **the package contents being bumped to are third-party code**. Green CI does not certify the code, it only certifies that the project's tests still pass.

## When to Use

- Reviewing PRs opened by Dependabot or Renovate.
- Reviewing manual dependency-bump PRs.
- When `gh pr list` surfaces dependency update PRs and the user asks which to merge.

## Checklist (Phase 1 → 2 → 3)

If any phase surfaces a blocker, classify the PR as **do-not-merge** immediately and stop the checklist there.

### Phase 1: Basic verification

```bash
# List all open PRs
gh pr list --state open --json number,title,headRefName,labels

# Inspect a specific PR
gh pr view <NUMBER> --json title,mergeable,mergeStateStatus,statusCheckRollup,files,additions,deletions
```

- [ ] **CI status**: every matrix cell (OS × language version) is SUCCESS.
  - CANCELLED only → decide whether to re-run.
  - FAILURE → inspect with `gh run view <RUN_ID> --log-failed`.
- [ ] **Mergeability**: `mergeable=MERGEABLE` and `mergeStateStatus=CLEAN`.
- [ ] **Version-jump class**:
  - **patch** (x.y.Z): low risk, usually mergeable.
  - **minor** (x.Y.0): medium risk, changelog review required.
  - **major** (X.0.0): high risk, every phase must be completed in full.

### Phase 2: Security verification

- [ ] **GitHub Security Advisory**:
  - `gh api repos/{owner}/{repo}/vulnerability-alerts` or the GitHub Security tab.
  - Does the target package have a known vulnerability?
  - Does the update itself include a security fix? (If yes, raise the priority.)
- [ ] **Package trust signals**:
  - **Official org?** `actions/*`, `github/*`, `golang.org/x/*` etc. → high trust.
  - **Maintenance health**: last-updated date, maintainer count, activity.
  - **Anomaly detection**: sudden change in download count or star count → typosquatting signal.
  - **New maintainer added**: possible account takeover.
- [ ] **Transitive dependencies**: the diff in `go.sum`, `package-lock.json`, etc. should not be unexpectedly large.
- [ ] **GitHub Actions specific**: prefer commit-SHA pinning (`@sha`) over tag pinning (`@v6`).

### Phase 3: Change-impact analysis

- [ ] **Breaking changes**:
  - Read release notes / changelog for breaking changes.
  - API changes, removed features, behavioral changes.
- [ ] **Language-version requirement bumps**:
  - `go` directive in `go.mod`, `engines` field, etc.
  - **Always confirm compatibility with the lowest version in the CI matrix**.
  - Example: dependency requires `go 1.24` but CI still has `go 1.19` → do-not-merge.
- [ ] **Project-specific dependency manifests**:
  - Does an `alldeps`-style file need updating?
  - Lock-file consistency.

## Verdict criteria

| Verdict | Conditions |
|---------|------------|
| **Merge** | CI fully green + no security concerns + no breaking changes |
| **Caution** | Major bump + CI fully green + no security concerns (breaking changes exist but impact is bounded) |
| **Do-not-merge** | CI failure / security concern / compatibility break |

## Report format

Present the verdicts to the user in this shape:

```
| PR | Version change | CI | Security | Breaking | Verdict | Recommended action |
|----|---------------|----|----------|----------|---------|--------------------|
```

State the reasoning for each PR concisely and recommend an action (`merge` / `close` / `hold`).

**Execute the recommended action only after explicit user approval.** Never auto-execute the merge.

## Common Mistakes

| Mistake | Correct response |
|---------|------------------|
| Merging on CI status alone | Run the security and impact phases too |
| Treating a major bump as routine | Always inspect breaking changes and compatibility |
| Assuming "Dependabot, so it's safe" | The bumped package is third-party code — verify it |
| Merging without reading the changelog | Always read the release notes for breaking changes |
| Ignoring transitive-dependency churn | Inspect the diff size of `go.sum` / lockfiles |
| Pinning Actions by tag | Prefer commit-SHA pinning |
| Batch-merging every PR | Merging one shifts the base for the rest — handle them serially |

## Red Flags — STOP before merging

- Any CI cell is FAILURE (CANCELLED-only needs investigation, not immediate stop).
- Major-version bump with an unread changelog.
- Language-version requirement increased (`go` directive, `engines`, etc.).
- Package maintainer changed recently.
- Transitive-dependency diff is unusually large.
- A relevant Security Advisory exists.

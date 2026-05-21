---
name: bump-plugin-version
description: Use when bumping a plugin's version in this marketplace — updates the entry in .claude-plugin/marketplace.json and plugins/<name>/.claude-plugin/plugin.json atomically so the two never drift
disable-model-invocation: true
---

# bump-plugin-version

Mechanizes the `CLAUDE.local.md` rule: when bumping a plugin's version, the entry in `marketplace.json` and the `version` field in `plugin.json` must stay in sync.

## How to use

Take `<plugin-name>` and `<new-version>` (semver, e.g. `0.2.0`) from the user, then:

1. From the repository root, run the bump script:

   ```bash
   ./.claude/skills/bump-plugin-version/scripts/bump.sh <plugin-name> <new-version>
   ```

2. Inspect the result with `git diff -- .claude-plugin/marketplace.json plugins/<plugin-name>/.claude-plugin/plugin.json` and report that the version is now `<new-version>` in both files.

3. Verify:
   - `jq -e --arg n "<plugin-name>" --arg v "<new-version>" '.plugins[] | select(.name == $n) | .version == $v' .claude-plugin/marketplace.json`
   - `jq -e --arg v "<new-version>" '.version == $v' plugins/<plugin-name>/.claude-plugin/plugin.json`
   - Both must return `true`.

## Arguments

- `<plugin-name>` (required): a plugin already registered in `marketplace.json`
- `<new-version>` (required): semver `MAJOR.MINOR.PATCH[-pre][+build]`

## Failure modes

The script exits 1 without writing anything if:

- `<plugin-name>` is not registered in `marketplace.json`
- `plugins/<plugin-name>/.claude-plugin/plugin.json` does not exist
- `<new-version>` is not valid semver

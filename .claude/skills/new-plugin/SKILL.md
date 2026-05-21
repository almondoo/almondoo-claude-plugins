---
name: new-plugin
description: Use when adding a new plugin to this marketplace — scaffolds plugins/<name>/ with plugin.json, a starter SKILL.md, and README, then registers the entry in .claude-plugin/marketplace.json
disable-model-invocation: true
---

# new-plugin

Use when adding a new plugin to the `almondoo-claude-plugins` marketplace. Executes the three-step workflow documented in `README.md` (create directory / write `plugin.json` / register in `marketplace.json`) in a single command.

## How to use

Take `<plugin-name>` (required) and `<description>` (optional) from the user. Verify `<plugin-name>` is kebab-case (lowercase letters, digits, hyphens) before running.

1. From the repository root, run the scaffold script:

   ```bash
   ./.claude/skills/new-plugin/scripts/scaffold.sh <plugin-name> "<description>"
   ```

2. Inspect the result with `git status` and report:
   - The files generated under `plugins/<plugin-name>/`
   - The new entry added to `.claude-plugin/marketplace.json`

3. Verify (per the `CLAUDE.local.md` rules):
   - `jq . .claude-plugin/marketplace.json` — root manifest is valid
   - `jq . plugins/<plugin-name>/.claude-plugin/plugin.json` — plugin manifest is valid
   - The frontmatter `name` of `plugins/<plugin-name>/skills/<plugin-name>/SKILL.md` matches its directory name

4. Suggest the next actions:
   - Fill in the body of the generated `SKILL.md` (currently a TODO placeholder)
   - Edit `plugins/<plugin-name>/README.md`
   - Adjust `category` and `keywords` in `marketplace.json` if `productivity` / `[]` are not appropriate

## Arguments

- `<plugin-name>` (required): kebab-case (lowercase letters, digits, hyphens)
- `<description>` (optional): one or two sentences written into both `marketplace.json` and `plugin.json`. A TODO placeholder is used if omitted.

## Failure modes

- The script exits 1 without writing anything if `plugins/<plugin-name>/` already exists, if the plugin name is already registered in `marketplace.json`, or if `marketplace.json` cannot be parsed.

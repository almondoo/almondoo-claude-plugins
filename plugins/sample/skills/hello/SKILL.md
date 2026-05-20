---
name: hello
description: >
  Minimal sample skill bundled with the `sample` plugin. Use when the user
  invokes `/sample:hello`, or asks for a starter / template skill, or wants
  to verify that the `almondoo-claude-plugins` marketplace and `sample`
  plugin are installed correctly. Replies with a single-line greeting that
  includes the current working directory and git branch.
---

# hello — sample skill

The simplest possible Claude Code skill. Confirms that:

- the `almondoo-claude-plugins` marketplace is added,
- the `sample` plugin is installed, and
- skills inside the plugin are discoverable as `/sample:hello`.

## Steps to perform when invoked

1. Determine the current working directory (e.g. read `$PWD` or run `pwd`).
2. Determine the current git branch with `git branch --show-current`. If the
   directory is not a git repository, treat the branch as `(none)`.
3. Reply with exactly one line in this format:

   ```
   Hello from sample plugin — cwd=<directory> branch=<branch>
   ```

Do not perform any other action. This skill is intentionally trivial — its
purpose is to act as a template and a smoke test.

## Using this as a template

Copy `plugins/sample/skills/hello/` to a new directory, update the
frontmatter (`name`, `description`) to describe the new skill, and replace
the steps with the real procedure. Register the parent plugin in the
top-level `.claude-plugin/marketplace.json`.

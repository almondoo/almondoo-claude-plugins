#!/usr/bin/env bash
# Scaffold a new plugin under plugins/<name>/ and register it in
# .claude-plugin/marketplace.json. Run from the repository root.
#
# Usage:
#   ./.claude/skills/new-plugin/scripts/scaffold.sh <plugin-name> [description]

set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "usage: $0 <plugin-name> [description]" >&2
  exit 2
fi

NAME="$1"
DESC="${2:-TODO: write a one-line description for $NAME.}"

if ! [[ "$NAME" =~ ^[a-z0-9]([a-z0-9-]*[a-z0-9])?$ ]]; then
  echo "error: plugin name must be kebab-case (lowercase letters, digits, hyphens), got: $NAME" >&2
  exit 1
fi

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT"

MARKETPLACE=".claude-plugin/marketplace.json"
PLUGIN_DIR="plugins/$NAME"

if [ ! -f "$MARKETPLACE" ]; then
  echo "error: $MARKETPLACE not found — run from the marketplace repository root" >&2
  exit 1
fi

if [ -e "$PLUGIN_DIR" ]; then
  echo "error: $PLUGIN_DIR already exists" >&2
  exit 1
fi

if jq -e --arg n "$NAME" '.plugins[] | select(.name == $n)' "$MARKETPLACE" >/dev/null; then
  echo "error: plugin '$NAME' is already registered in $MARKETPLACE" >&2
  exit 1
fi

mkdir -p "$PLUGIN_DIR/.claude-plugin" "$PLUGIN_DIR/skills/$NAME"

cat > "$PLUGIN_DIR/.claude-plugin/plugin.json" <<JSON
{
  "name": "$NAME",
  "version": "0.1.0",
  "description": "$DESC"
}
JSON

cat > "$PLUGIN_DIR/skills/$NAME/SKILL.md" <<MD
---
name: $NAME
description: TODO — describe when Claude should use this skill (start with "Use when...")
---

# $NAME

TODO: write the skill body.
MD

cat > "$PLUGIN_DIR/README.md" <<MD
# $NAME

$DESC

## Install

\`\`\`
/plugin install $NAME@almondoo-claude-plugins
\`\`\`
MD

TMP="$(mktemp)"
jq --arg n "$NAME" --arg d "$DESC" --arg s "./plugins/$NAME" '
  .plugins += [{
    name: $n,
    description: $d,
    source: $s,
    version: "0.1.0",
    category: "productivity",
    keywords: []
  }]
' "$MARKETPLACE" > "$TMP"
mv "$TMP" "$MARKETPLACE"

jq . "$MARKETPLACE" >/dev/null
jq . "$PLUGIN_DIR/.claude-plugin/plugin.json" >/dev/null

echo "✓ scaffolded $PLUGIN_DIR/"
echo "✓ registered '$NAME' in $MARKETPLACE"
echo
echo "next steps:"
echo "  - edit $PLUGIN_DIR/skills/$NAME/SKILL.md (replace TODO)"
echo "  - edit $PLUGIN_DIR/README.md"
echo "  - fill in keywords/category in $MARKETPLACE if needed"

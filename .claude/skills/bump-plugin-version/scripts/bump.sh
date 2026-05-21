#!/usr/bin/env bash
# Bump a plugin's version in both .claude-plugin/marketplace.json and
# plugins/<name>/.claude-plugin/plugin.json. Run from the repository root.
#
# Usage:
#   ./.claude/skills/bump-plugin-version/scripts/bump.sh <plugin-name> <new-version>

set -euo pipefail

if [ "$#" -ne 2 ]; then
  echo "usage: $0 <plugin-name> <new-version>" >&2
  exit 2
fi

NAME="$1"
VERSION="$2"

if ! [[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.-]+)?(\+[0-9A-Za-z.-]+)?$ ]]; then
  echo "error: '$VERSION' does not look like a semver (MAJOR.MINOR.PATCH[-pre][+build])" >&2
  exit 1
fi

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT"

MARKETPLACE=".claude-plugin/marketplace.json"
PLUGIN_MANIFEST="plugins/$NAME/.claude-plugin/plugin.json"

if [ ! -f "$MARKETPLACE" ]; then
  echo "error: $MARKETPLACE not found — run from the marketplace repository root" >&2
  exit 1
fi

if [ ! -f "$PLUGIN_MANIFEST" ]; then
  echo "error: $PLUGIN_MANIFEST not found" >&2
  exit 1
fi

if ! jq -e --arg n "$NAME" '.plugins[] | select(.name == $n)' "$MARKETPLACE" >/dev/null; then
  echo "error: plugin '$NAME' is not registered in $MARKETPLACE" >&2
  exit 1
fi

CURRENT_MP=$(jq -r --arg n "$NAME" '.plugins[] | select(.name == $n) | .version' "$MARKETPLACE")
CURRENT_PL=$(jq -r '.version // ""' "$PLUGIN_MANIFEST")

TMP_MP="$(mktemp)"
TMP_PL="$(mktemp)"

jq --arg n "$NAME" --arg v "$VERSION" '
  .plugins |= map(if .name == $n then .version = $v else . end)
' "$MARKETPLACE" > "$TMP_MP"

jq --arg v "$VERSION" '.version = $v' "$PLUGIN_MANIFEST" > "$TMP_PL"

mv "$TMP_MP" "$MARKETPLACE"
mv "$TMP_PL" "$PLUGIN_MANIFEST"

jq . "$MARKETPLACE" >/dev/null
jq . "$PLUGIN_MANIFEST" >/dev/null

echo "✓ $MARKETPLACE: $CURRENT_MP → $VERSION"
echo "✓ $PLUGIN_MANIFEST: $CURRENT_PL → $VERSION"

#!/usr/bin/env bash
# PostToolUse hook for Edit / Write / MultiEdit.
# - If the edited file is *.json, validate it with `jq .`
# - If the edited file is */SKILL.md, ensure its frontmatter `name`
#   matches its parent directory name (Claude Code skill convention).
#
# Exit codes:
#   0  → silent success (or non-applicable file type)
#   2  → validation failure (shown to Claude; lets it self-correct)
#
# Per CLAUDE.local.md verification rules.

set -u

INPUT="$(cat)"
FILE="$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null || true)"

[ -z "$FILE" ] && exit 0
[ ! -f "$FILE" ] && exit 0

case "$FILE" in
  *.json)
    if ! jq . "$FILE" >/dev/null 2>&1; then
      echo "✗ invalid JSON after edit: $FILE" >&2
      jq . "$FILE" 2>&1 >/dev/null | head -5 >&2 || true
      exit 2
    fi
    ;;
  */SKILL.md)
    DIR_NAME="$(basename "$(dirname "$FILE")")"
    SKILL_NAME="$(awk '
      /^---[[:space:]]*$/ { fm = !fm; next }
      fm && /^name:[[:space:]]*/ {
        sub(/^name:[[:space:]]*/, "")
        gsub(/^["'\'']|["'\'']$/, "")
        print
        exit
      }
    ' "$FILE")"
    if [ -z "$SKILL_NAME" ]; then
      echo "✗ $FILE: frontmatter is missing a 'name:' field" >&2
      exit 2
    fi
    if [ "$DIR_NAME" != "$SKILL_NAME" ]; then
      echo "✗ $FILE: frontmatter name '$SKILL_NAME' does not match directory '$DIR_NAME'" >&2
      exit 2
    fi
    ;;
esac

exit 0

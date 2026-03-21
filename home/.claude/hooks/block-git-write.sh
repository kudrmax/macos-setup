#!/bin/bash
# Block git write operations, allow read-only ones.
# Used as a PreToolUse hook for Bash in Claude Code.

cmd=$(jq -r '.command')

# No git command — allow
if ! echo "$cmd" | grep -qE '\bgit\b'; then
  exit 0
fi

# Read-only git subcommands — allow
readonly_cmds="status|log|diff|show|blame|remote|rev-parse|describe|shortlog|reflog|ls-files|ls-tree|cat-file|name-rev|config|version|help|for-each-ref|count-objects|fsck|verify-pack"
if echo "$cmd" | grep -qE "\bgit\s+($readonly_cmds)\b"; then
  exit 0
fi

# git branch/tag listing (no modification flags) — allow
if echo "$cmd" | grep -qE '\bgit\s+branch(\s*$|\s+-[avrl]|\s+--list)'; then
  exit 0
fi
if echo "$cmd" | grep -qE '\bgit\s+tag(\s*$|\s+-l\b|\s+--list)'; then
  exit 0
fi

# git stash list — allow
if echo "$cmd" | grep -qE '\bgit\s+stash\s+list'; then
  exit 0
fi

# Everything else (commit, push, pull, merge, rebase, reset, checkout, add, rm, etc.) — block
echo "BLOCKED: git write operation — ask user for explicit confirmation" >&2
exit 2

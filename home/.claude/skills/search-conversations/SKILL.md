---
name: search-conversations
description: Use when the user asks to find something from a past conversation, recall what was discussed, or search through Claude Code session history
---

# Search Conversations

Search all past Claude Code sessions across all projects.

## File Structure

- `~/.claude/history.jsonl` — index of ALL user messages (all projects, all sessions). Each line is JSON with `display` (message text), `sessionId`, `project`, `timestamp`.
- `~/.claude/projects/<project-path>/<sessionId>.jsonl` — full conversation log (user + assistant + tool calls). Lines are large JSON objects.

## How to Search

**Step 1: Find the session** — grep `history.jsonl` for keywords:

```bash
Grep pattern="keyword" path="~/.claude/history.jsonl" output_mode="content"
```

This returns matching user messages with `sessionId` and `project` path.

**Step 2: Read the full conversation** — construct path from step 1:

```
~/.claude/projects/<project-path>/<sessionId>.jsonl
```

Grep or Read this file for detailed context (assistant responses, tool calls, etc.).

## Tips

- `history.jsonl` contains only user messages — fast to search, small lines
- Session `.jsonl` files contain everything (tool results are huge) — use Grep with specific patterns, not Read on entire file
- `project` field in history.jsonl uses the path format `-Users-name-path-to-project` (hyphens instead of slashes)
- Use `-i` flag for case-insensitive search
- To narrow by date, grep for `timestamp` ranges or look at surrounding context

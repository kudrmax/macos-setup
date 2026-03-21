---
name: youtube-search
description: Search YouTube videos by query using yt-dlp. Returns title, views, author, duration, date, and URL.
argument-hint: <query> [count]
allowed-tools: Bash
---

# YouTube Search

Search YouTube for videos matching the user's query using `yt-dlp`.

## Arguments

- `$ARGUMENTS` — search query, optionally followed by result count (default: 5)

## Instructions

1. Parse `$ARGUMENTS`: extract the search query and optional count (last token if it's a number, otherwise default to 5, max 20).
2. Run the following command, replacing `{query}` and `{count}`:

```bash
yt-dlp "ytsearch{count}:{query}" --no-download --print "%(title)s | %(view_count)s | %(channel)s | %(duration_string)s | %(upload_date>%Y-%m-%d)s | %(webpage_url)s" 2>/dev/null
```

3. Format results as a markdown table:

| # | Title | Views | Author | Duration | Date | URL |
|---|-------|-------|--------|----------|------|-----|

- Format view counts with thousands separators (e.g., 1,234,567)
- Keep titles concise — truncate to 60 chars if needed
- Make URL clickable

4. If no results found, inform the user.

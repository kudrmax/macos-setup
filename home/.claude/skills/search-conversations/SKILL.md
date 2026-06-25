---
name: search-conversations
description: Use when the user asks to find, recall, or resume a past Claude Code session — "where did we do X", "that session where you wrote/created Y", "the one that ended with Z", "find the chat about W". Especially when the user is vague, misremembers, or describes the session by its OUTCOME or an artifact you produced rather than their own words.
---

# Search Conversations

Find a past Claude Code session across all projects.

## Core principle

**Topic does not identify a session — a discriminator does.** The user has many
sessions on the same topic ("config", "the PR", "rassrochka"). What singles one
out is usually something on the ASSISTANT side: a file you created, how the
session ENDED, its AI-title — NOT the words the user typed.

**The user is an unreliable narrator.** They misremember, use wrong words, lead
with the wrong detail. Translate their phrasing into *signals*, search several
layers, then **confirm the candidate against the discriminator before naming
it.** Never let topic-similarity alone pick the answer.

## Where the signals live

| The session is remembered by… | Search this | Why grep of `history.jsonl` misses it |
|---|---|---|
| What the USER asked | `~/.claude/history.jsonl` (user msgs only) | — (this is what it holds) |
| An artifact YOU made ("you wrote the instruction / created the file / the script") | `tool_use` `Write`/`Edit` `file_path` inside session `.jsonl` | assistant side, not in history.jsonl |
| How it ENDED ("we finished on…") | last assistant message of each session | assistant side |
| The TOPIC ("the config one") | `aiTitle` record in each session | assistant side; may be in the other language |
| Something you SAID | assistant text inside session `.jsonl` | assistant side |

## Primary tool

`index_sessions.py` surfaces all four discriminators at once — title, opening
ask, final reply, files touched — one block per session:

```bash
python3 ~/.claude/skills/search-conversations/index_sessions.py <project-dir> [FILTER]
python3 ~/.claude/skills/search-conversations/index_sessions.py all "config,конфиг,setup"
```

Run `--help` for details. Read the map and match the user's discriminator to a
block. This alone answers most requests — reach for raw grep only to dig deeper.

## Workflow

1. **Decompose the request into signals** — topic? an artifact you created? how
   it ended? a phrase you said? a date/project? Note which is the *discriminator*
   (the detail that separates the target from same-topic siblings).
2. **Build the map**: `index_sessions.py <project>`. Add a FILTER only to narrow,
   with synonyms AND both languages (`config,конфиг,setup,инструкц`) — one word
   silently drops the target.
3. **Shortlist** by the discriminator, not by topic. Same-topic siblings are
   expected — that's the trap.
4. **Confirm before naming**: open the candidate's `.jsonl` and verify the
   discriminator is actually there (the final message really is the instruction;
   the file really was created). State *what* confirmed it.
5. **Hand back the verified id** (see below) for `/resume`.

## NEVER hand-type the sessionId

`sessionId` is an opaque UUID. NEVER retype it, reconstruct it from memory, or
copy it into a variable you typed — the model silently corrupts bytes in long
opaque strings (`…c396d2` → `…c536d2`), and the error stays hidden until
`/resume` fails. Carry it byte-for-byte from tool output (`index_sessions.py`
prints it on the `id:` line). Don't match session files with a prefix glob
(`cabff4db*.jsonl`) — a glob hides a typo by matching the real file anyway.

## Common mistakes (these are how it goes wrong)

| Mistake | Do instead |
|---|---|
| Picking the session whose topic matches best | Match the discriminator; topic is shared by siblings |
| Filtering by one literal word from the request | OR several synonyms + both languages; or no filter, read the map |
| Naming a candidate before opening it | Confirm the discriminator inside the `.jsonl` first |
| When the user says "wrong session", inventing why you're still right | Re-open and check the discriminator; a doubted answer is unverified |
| Searching only `history.jsonl` | It's user-only — the memorable detail is usually assistant-side |

## Red flags — STOP

- "It's clearly the config one" → which discriminator? topic ≠ identity.
- "Filter returned nothing, so nothing matches" → wrong/one-language word, not absence.
- "Probably this one" said without having opened the file.
- Defending a pick after the user pushed back, instead of re-checking.
